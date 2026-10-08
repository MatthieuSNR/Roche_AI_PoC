"""
Statistics engine: computes all numeric insights from the filtered comments.
Used by the Streamlit dashboard (charts) and the LLM AI Summary (facts).
All numbers are computed by pandas — the LLM never counts.

The unit is a COMMENT (one row of cleaned_comments.csv = one comment on one material
of one vendor). Shares are always "X% of the comments of the current selection"; when a
filter is active they are compared with the same share over all comments.
"""

import pandas as pd

NO_ROOT_CAUSE = "(no root cause)"


def _pct(part, total):
    return round(part / total * 100, 1) if total else 0.0


def _share_table(series: pd.Series, top: int = 5) -> dict:
    """{value: {"comments": n, "pct": share of the selection}} for the most frequent values."""
    counts = series.value_counts()
    return {
        str(k): {"comments": int(v), "pct": _pct(v, len(series))}
        for k, v in counts.head(top).items()
    }


def weekly_active(df: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    """Number of comments visible in the dashboard each week (optionally split by a column).
    A comment counts in a week if First_Seen <= week end and Last_Seen >= week start."""
    if df.empty:
        return pd.DataFrame()
    first, last = pd.to_datetime(df["First_Seen"]), pd.to_datetime(df["Last_Seen"])
    weeks = pd.date_range(first.min().normalize(), last.max().normalize(), freq="W-SUN")
    rows = {}
    for week_end in weeks:
        week_start = week_end - pd.Timedelta(days=6)
        active = df[(first <= week_end) & (last >= week_start)]
        rows[week_end] = active[by].value_counts() if by else pd.Series({"Comments": len(active)})
    return pd.DataFrame(rows).T.fillna(0).astype(int).sort_index()


def compute_stats(filtered_df: pd.DataFrame, all_df: pd.DataFrame | None = None) -> dict:
    """Compute key statistics for the currently filtered data.
    all_df (all comments, no filter) is used for the comparisons "vs all comments"."""

    filtered_df = filtered_df.copy()  # Avoid mutating the caller's dataframe
    all_df = filtered_df if all_df is None else all_df
    n = len(filtered_df)

    stats = {
        "total_comments": n,
        "share_of_all_comments_pct": _pct(n, len(all_df)),
    }
    if filtered_df.empty:
        return stats

    # 1. Root cause distribution (share of the comments of the selection)
    causes = filtered_df["Root_Cause"].fillna(NO_ROOT_CAUSE)
    all_causes = all_df["Root_Cause"].fillna(NO_ROOT_CAUSE)
    stats["root_cause_coverage_pct"] = _pct(filtered_df["Root_Cause"].notna().sum(), n)
    with_cause = causes[causes != NO_ROOT_CAUSE]
    cause_counts = with_cause.value_counts()
    stats["top_root_causes"] = {c: int(k) for c, k in cause_counts.head(5).items()}
    stats["top_root_causes_pct"] = {c: _pct(k, n) for c, k in cause_counts.head(5).items()}
    # Same root cause over all comments: is it over-represented in this selection?
    stats["top_root_causes_pct_all"] = {
        c: _pct((all_causes == c).sum(), len(all_df)) for c in cause_counts.head(5).index
    }

    # 2. Who writes / is concerned: vendors and MRP controllers (share of the selection)
    stats["top_vendors"] = _share_table(filtered_df["VENDOR_NAME"].fillna("Unknown vendor"))
    stats["top_mrp_controllers"] = _share_table(filtered_df["MRP_CONTROLLER"].fillna("Unknown"))
    stats["vendor_count"] = int(filtered_df["VENDOR_NAME"].nunique())
    stats["mrp_controller_count"] = int(filtered_df["MRP_CONTROLLER"].nunique())
    stats["material_count"] = int(filtered_df["MATERIAL_NUMBER"].nunique())

    # 3. Persistence: how long do the comments stay in the dashboard?
    latest_snapshot = pd.to_datetime(all_df["Last_Seen"]).max()
    still_open = pd.to_datetime(filtered_df["Last_Seen"]) == latest_snapshot
    stats["latest_snapshot"] = str(latest_snapshot.date())
    stats["comments_still_open"] = int(still_open.sum())
    stats["comments_still_open_pct"] = _pct(still_open.sum(), n)
    stats["median_days_active"] = float(filtered_df["Days_Active"].median())
    stats["median_days_active_all"] = float(all_df["Days_Active"].median())

    # 4. Trend: comments visible per week, first vs last week of the selection
    weekly = weekly_active(filtered_df)
    if len(weekly) >= 2:
        stats["first_snapshot"] = str(weekly.index[0].date())
        stats["last_snapshot"] = str(weekly.index[-1].date())
        stats["comments_first_snapshot"] = int(weekly["Comments"].iloc[0])
        stats["comments_last_snapshot"] = int(weekly["Comments"].iloc[-1])
        if weekly["Comments"].iloc[0]:
            stats["trend_pct"] = _pct(weekly["Comments"].iloc[-1] - weekly["Comments"].iloc[0],
                                      weekly["Comments"].iloc[0])

        # Root causes that increased the most between the first and last week
        by_cause = weekly_active(filtered_df.assign(Root_Cause=causes), by="Root_Cause")
        by_cause = by_cause.drop(columns=[NO_ROOT_CAUSE], errors="ignore")
        if not by_cause.empty:
            diff = by_cause.iloc[-1] - by_cause.iloc[0]
            stats["causes_increasing"] = {
                c: int(d) for c, d in diff[diff > 0].sort_values(ascending=False).head(3).items()
            }
            stats["causes_decreasing"] = {
                c: int(d) for c, d in diff[diff < 0].sort_values().head(3).items()
            }

    # 5. Material status distribution
    if "MATERIAL_STATUS" in filtered_df.columns:
        stats["material_status_counts"] = {
            s: int(c) for s, c in filtered_df["MATERIAL_STATUS"].value_counts().items()
        }

    # 6. Impact distribution
    if "Impact" in filtered_df.columns:
        stats["impact_counts"] = {
            i: int(c) for i, c in filtered_df["Impact"].value_counts().items()
        }

    # 7. Language: share of comments written in German (translated with DeepL)
    if "comment_language" in filtered_df.columns:
        stats["german_comments_pct"] = _pct((filtered_df["comment_language"] == "de").sum(), n)

    # 8. Most frequent comments (verbatim for the LLM)
    stats["top_comments"] = [
        c for c in filtered_df["Comment_EN"].value_counts().head(5).index
    ]

    return stats


def root_cause_sources(filtered_df: pd.DataFrame, root_cause: str, by: str, top: int = 5) -> pd.DataFrame:
    """Where does a root cause come from? For the comments with this root cause:
    share coming from each vendor / MRP controller, and how much of that entity's
    comments this root cause represents."""
    subset = filtered_df[filtered_df["Root_Cause"] == root_cause]
    if subset.empty:
        return pd.DataFrame()
    counts = subset[by].fillna("Unknown").value_counts().head(top)
    entity_totals = filtered_df[by].fillna("Unknown").value_counts()
    return pd.DataFrame({
        by: counts.index,
        "Comments": counts.values,
        f"% of '{root_cause}' comments": [_pct(c, len(subset)) for c in counts.values],
        "% of this entity's comments": [_pct(c, entity_totals[e]) for e, c in counts.items()],
    })

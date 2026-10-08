"""
Statistics engine: computes all numeric insights from the filtered comments.
Used by the Streamlit dashboard (charts) and the LLM AI Summary (facts).
All numbers are computed by pandas — the LLM never counts.
"""

import pandas as pd


def compute_stats(filtered_df: pd.DataFrame) -> dict:
    """Compute key statistics for the currently filtered data."""
    
    # Ensure Snapshot_Date is datetime 
    filtered_df = filtered_df.copy()  # Avoid mutating the caller's dataframe
    filtered_df["Snapshot_Date"] = pd.to_datetime(
        filtered_df["Snapshot_Date"], errors="coerce"
    )
    
    
    stats = {
        "total_comments": len(filtered_df),
    }
    if filtered_df.empty:
        return stats

    # 1. Root cause distribution
    cause_counts = filtered_df["Root_Cause"].value_counts()
    stats["top_root_causes"] = {
        cause: int(count) for cause, count in cause_counts.head(5).items()
    }
    stats["top_root_causes_pct"] = {
        cause: round(count / len(filtered_df) * 100, 1)
        for cause, count in cause_counts.head(5).items()
    }

    # 2. Trend: total comments first vs last snapshot
    by_date = filtered_df.dropna(subset=["Snapshot_Date"]).groupby("Snapshot_Date").size()
    if len(by_date) >= 2:
        stats["first_snapshot"] = str(by_date.index[0].date())
        stats["last_snapshot"] = str(by_date.index[-1].date())
        stats["comments_first_snapshot"] = int(by_date.iloc[0])
        stats["comments_last_snapshot"] = int(by_date.iloc[-1])
        stats["trend_pct"] = round(
            (by_date.iloc[-1] - by_date.iloc[0]) / by_date.iloc[0] * 100, 1
        )

    # 3. Root causes that increased the most between first and last snapshot
    if len(by_date) >= 2:
        first_date, last_date = by_date.index[0], by_date.index[-1]
        pivot = (
            filtered_df.dropna(subset=["Snapshot_Date"])
            .groupby(["Snapshot_Date", "Root_Cause"]).size().unstack(fill_value=0)
        )
        if first_date in pivot.index and last_date in pivot.index:
            diff = pivot.loc[last_date] - pivot.loc[first_date]
            stats["causes_increasing"] = {
                c: int(d) for c, d in diff[diff > 0].sort_values(ascending=False).head(3).items()
            }
            stats["causes_decreasing"] = {
                c: int(d) for c, d in diff[diff < 0].sort_values().head(3).items()
            }

    # 4. Material status distribution
    if "MATERIAL_STATUS" in filtered_df.columns:
        stats["material_status_counts"] = {
            s: int(c) for s, c in filtered_df["MATERIAL_STATUS"].value_counts().items()
        }

    # 5. Impact distribution
    if "Impact" in filtered_df.columns:
        stats["impact_counts"] = {
            i: int(c) for i, c in filtered_df["Impact"].value_counts().items()
        }

    # 6. Most frequent comments (verbatim for the LLM)
    stats["top_comments"] = [
        c for c in filtered_df["Comment_EN"].value_counts().head(5).index
    ]

    # 7. Vendors affected (if multiple)
    if "VENDOR_NAME" in filtered_df.columns:
        stats["vendor_count"] = int(filtered_df["VENDOR_NAME"].nunique())

    return stats
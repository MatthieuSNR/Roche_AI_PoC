"""One profile for any level: vendor, MRP controller or material.

``build_profile`` returns the SAME JSON-safe dictionary whatever the level, so that
the dashboard renders it with one function and the LLM receives it as its only
source of figures (pandas computes, the LLM only phrases).
"""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
import pandas as pd

from roche_poc import config
from roche_poc.stats import kpis, persistence, trends, watchlist as wl

Level = Literal["vendor", "mrp_controller", "material"]
_STATUS_RANK = {s: i for i, s in enumerate(config.STATUS_ORDER)}


def comment_text_column(comments: pd.DataFrame) -> str:
    """English text when the translation step was run, original text otherwise."""
    return config.COL_COMMENT_EN if config.COL_COMMENT_EN in comments.columns else config.COL_COMMENT


def jsonable(obj: Any) -> Any:
    """Recursively convert numpy / pandas scalars to plain Python (NaN -> None)."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, np.datetime64)):
        return None if pd.isna(obj) else str(pd.Timestamp(obj).date())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if math.isnan(float(obj)) else float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if obj is pd.NA or obj is pd.NaT:
        return None
    return obj


def portfolio_benchmark(snapshots: pd.DataFrame, level: Level) -> pd.Series:
    """Critical share of every entity at the latest snapshot (for comparison)."""
    col = config.LEVEL_COLUMNS[level]
    now = kpis.latest_rows(snapshots)
    return now.assign(_c=kpis.is_critical(now)).groupby(col)["_c"].mean()


def _worst_status(statuses: pd.Series) -> str | None:
    known = statuses.dropna()
    return None if known.empty else max(known, key=lambda s: _STATUS_RANK.get(s, -1))


def _material_table(scope: pd.DataFrame, streaks: pd.DataFrame, flags: pd.DataFrame, top_n: int) -> list[dict]:
    """Most problematic materials of a vendor / MRP controller (drill-down list)."""
    now = kpis.latest_rows(scope)
    if now.empty:
        return []
    per_material = now.groupby(config.COL_MATERIAL).agg(
        description=(config.COL_MATERIAL_DESC, "first"),
        status=(config.COL_STATUS, _worst_status),
        impact=(config.COL_IMPACT, "last"),
        root_cause=(config.COL_ROOT_CAUSE, "last"),
    )
    table = per_material.join(streaks, how="left")
    table["alerts"] = flags.groupby(config.COL_MATERIAL).size().reindex(table.index).fillna(0).astype(int)
    table[["n_critical_snapshots", "current_streak", "episodes"]] = (
        table[["n_critical_snapshots", "current_streak", "episodes"]].fillna(0).astype(int)
    )
    table["_sev"] = table["status"].map(_STATUS_RANK).fillna(-1)
    table = table.sort_values(
        ["_sev", "current_streak", "n_critical_snapshots"], ascending=False
    ).head(top_n)
    return table.drop(columns=["first_critical", "last_critical", "_sev"]).reset_index().to_dict("records")


def build_profile(
    snapshots: pd.DataFrame,
    comments: pd.DataFrame,
    level: Level,
    entity_id,
    top_n: int = config.TOP_N,
    n_recent_comments: int = 8,
    streaks: pd.DataFrame | None = None,
) -> dict:
    """Profile of one entity: current state, history, root causes, alerts, comments.

    ``streaks`` (portfolio-wide ``critical_streaks``) can be passed in to avoid
    recomputing it for every entity (the dashboard computes it once and caches it).
    """
    col = config.LEVEL_COLUMNS[level]
    scope = snapshots[snapshots[col] == entity_id]
    profile: dict = {"level": level, "entity_id": entity_id, "empty": scope.empty}
    if scope.empty:
        return jsonable(profile)

    portfolio_latest = kpis.latest_snapshot(snapshots)
    now = kpis.latest_rows(scope, portfolio_latest)
    if streaks is None:
        streaks = persistence.critical_streaks(snapshots)  # portfolio-wide: consistent definition
    scope_streaks = streaks.loc[streaks.index.intersection(scope[config.COL_MATERIAL].unique())]
    flags = wl.build_watchlist(scope)
    critical_share_series = kpis.critical_share_timeline(scope)

    benchmark = portfolio_benchmark(snapshots, level)
    entity_share = kpis.critical_share(now) if len(now) else float("nan")
    percentile = (
        None if math.isnan(entity_share) or benchmark.empty
        else round(float((benchmark < entity_share).mean() * 100), 0)
    )

    first_snapshot = pd.to_datetime(scope[config.COL_SNAPSHOT]).min()
    profile.update(
        meta={
            "label": str(entity_id),
            "first_snapshot": first_snapshot,
            "last_snapshot": portfolio_latest,
            "n_snapshots": int(scope[config.COL_SNAPSHOT].nunique()),
            "n_rows": int(len(scope)),
            "n_materials": int(scope[config.COL_MATERIAL].nunique()),
            "in_latest_snapshot": bool(len(now)),
        },
        current={
            "elements": int(len(now)),
            "materials": int(now[config.COL_MATERIAL].nunique()),
            "status_counts": kpis.status_counts(now),
            "impact_counts": kpis.impact_counts(now),
            "critical_share_pct": None if math.isnan(entity_share) else round(100 * entity_share, 1),
            "portfolio_median_critical_share_pct": (
                None if benchmark.empty else round(100 * float(benchmark.median()), 1)
            ),
            "percentile_vs_portfolio": percentile,
        },
        history={
            "status_timeline": kpis.status_timeline(scope).reset_index().to_dict("records"),
            "critical_share_trend": trends.trend_summary(critical_share_series),
            "critical_share_series": critical_share_series.reset_index().to_dict("records"),
        },
        root_causes={
            "table": kpis.root_cause_table(scope, top_n).to_dict("records"),
            "critical_coverage": kpis.root_cause_coverage(now),
            "history_coverage": kpis.root_cause_coverage(scope),
        },
        persistence={
            "chronic_materials": int((scope_streaks["current_streak"] >= config.PERSISTENT_CRITICAL_SNAPSHOTS).sum()),
            "recurrent_materials": int((scope_streaks["episodes"] >= config.RECURRENT_EPISODES).sum()),
            "max_current_streak": int(scope_streaks["current_streak"].max()) if len(scope_streaks) else 0,
        },
        watchlist={
            "n_high": int((flags["severity"] == wl.HIGH).sum()),
            "n_medium": int((flags["severity"] == wl.MEDIUM).sum()),
            "alerts": flags.head(25).to_dict("records"),
        },
    )

    if level == "material":
        by_vendor = (
            scope.assign(_c=kpis.is_critical(scope))
            .groupby(config.COL_VENDOR)
            .agg(rows=("_c", "size"), critical_share=("_c", "mean"), last_seen=(config.COL_SNAPSHOT, "max"))
            .sort_values("last_seen", ascending=False)
            .reset_index()
        )
        by_vendor["critical_share"] = by_vendor["critical_share"].round(3)
        profile["related_vendors"] = by_vendor.to_dict("records")
        profile["stockout_dates"] = sorted(
            {str(pd.Timestamp(d).date()) for d in scope[config.COL_STOCKOUT_DATE].dropna()}
        )[-10:] if config.COL_STOCKOUT_DATE in scope.columns else []
    else:
        profile["top_materials"] = _material_table(scope, streaks, flags, top_n)

    c_scope = comments[comments[col] == entity_id] if col in comments.columns else comments.iloc[0:0]
    text_col = comment_text_column(comments)
    recent = c_scope.sort_values("last_seen", ascending=False).head(n_recent_comments)
    profile["recent_comments"] = [
        {
            "last_seen": r["last_seen"],
            "root_cause": r.get(config.COL_ROOT_CAUSE),
            "impact": r.get(config.COL_IMPACT),
            "n_snapshots": r.get("n_snapshots"),
            "text": r[text_col],
        }
        for _, r in recent.iterrows()
    ]
    return jsonable(profile)


def portfolio_overview(snapshots: pd.DataFrame) -> dict:
    """Portfolio-level counterpart of a profile (home page of the dashboard)."""
    now = kpis.latest_rows(snapshots)
    flags = wl.build_watchlist(snapshots)
    return jsonable(
        {
            "last_snapshot": kpis.latest_snapshot(snapshots),
            "elements": len(now),
            "materials": now[config.COL_MATERIAL].nunique(),
            "status_counts": kpis.status_counts(now),
            "impact_counts": kpis.impact_counts(now),
            "critical_share_pct": round(100 * kpis.critical_share(now), 1),
            "root_cause_coverage": kpis.root_cause_coverage(now),
            "alerts_high": int((flags["severity"] == wl.HIGH).sum()),
            "alerts_medium": int((flags["severity"] == wl.MEDIUM).sum()),
            "status_timeline": kpis.status_timeline(snapshots).reset_index().to_dict("records"),
        }
    )

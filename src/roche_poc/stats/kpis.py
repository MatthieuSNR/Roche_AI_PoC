"""Basic indicators computed on the ``snapshots`` table (or any filtered subset of it).

Unit of count: one row = one MRP element in one snapshot ("element-snapshot").
Counting element-snapshots measures *exposure* (a problem that lasts ten weeks weighs
ten times more than a one-week problem); ``n_materials`` gives the distinct count.
"""

from __future__ import annotations

import pandas as pd

from roche_poc import config


def latest_snapshot(df: pd.DataFrame) -> pd.Timestamp:
    return pd.to_datetime(df[config.COL_SNAPSHOT]).max()


def latest_rows(df: pd.DataFrame, snapshot: pd.Timestamp | None = None) -> pd.DataFrame:
    """Rows of the most recent snapshot (or of ``snapshot`` when given)."""
    snapshot = snapshot if snapshot is not None else latest_snapshot(df)
    return df[pd.to_datetime(df[config.COL_SNAPSHOT]) == snapshot]


def is_critical(df: pd.DataFrame) -> pd.Series:
    """Boolean mask: Potential or Actual Stock Out."""
    return df[config.COL_STATUS].isin(config.CRITICAL_STATUSES)


def status_counts(df: pd.DataFrame) -> dict[str, int]:
    """Row count per status, in severity order, zeros included."""
    counts = df[config.COL_STATUS].value_counts()
    return {status: int(counts.get(status, 0)) for status in config.STATUS_ORDER}


def impact_counts(df: pd.DataFrame) -> dict[str, int]:
    """Row count per impact level, in severity order, zeros included."""
    if config.COL_IMPACT not in df.columns:
        return {}
    counts = df[config.COL_IMPACT].value_counts()
    return {impact: int(counts.get(impact, 0)) for impact in config.IMPACT_ORDER}


def critical_share(df: pd.DataFrame) -> float:
    """Share (0-1) of rows that are critical; NaN on an empty frame."""
    return float(is_critical(df).mean()) if len(df) else float("nan")


def status_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Rows per snapshot and status (index: snapshot date, columns: statuses in order)."""
    table = (
        df.assign(_snap=pd.to_datetime(df[config.COL_SNAPSHOT]))
        .groupby(["_snap", config.COL_STATUS])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=config.STATUS_ORDER, fill_value=0)
        .sort_index()
    )
    table.index.name = config.COL_SNAPSHOT
    return table


def critical_share_timeline(df: pd.DataFrame) -> pd.Series:
    """Share of critical rows at each snapshot (comparable across snapshots of unequal size)."""
    flagged = df.assign(_snap=pd.to_datetime(df[config.COL_SNAPSHOT]), _crit=is_critical(df))
    return flagged.groupby("_snap")["_crit"].mean().sort_index().rename("critical_share")


def root_cause_coverage(df: pd.DataFrame) -> dict:
    """How many critical rows carry a root cause (governance indicator).

    The process requires a root cause on every stock-out; a low coverage is itself
    a finding and must be shown next to any root-cause distribution.
    """
    critical = df[is_critical(df)]
    n = len(critical)
    with_cause = int(critical[config.COL_ROOT_CAUSE].notna().sum()) if n else 0
    return {
        "critical_rows": n,
        "with_root_cause": with_cause,
        "missing_pct": round(100 * (1 - with_cause / n), 1) if n else None,
    }


def root_cause_table(df: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
    """Root-cause distribution among rows that HAVE a root cause.

    Percentages use the rows with a known root cause as denominator, never the
    whole frame, so that missing values do not deflate the shares.
    """
    known = df[df[config.COL_ROOT_CAUSE].notna()]
    columns = [config.COL_ROOT_CAUSE, "n_rows", "n_materials", "pct_of_known"]
    if known.empty:
        return pd.DataFrame(columns=columns)
    table = (
        known.groupby(config.COL_ROOT_CAUSE)
        .agg(n_rows=(config.COL_ROOT_CAUSE, "size"), n_materials=(config.COL_MATERIAL, "nunique"))
        .sort_values("n_rows", ascending=False)
        .reset_index()
    )
    table["pct_of_known"] = (100 * table["n_rows"] / table["n_rows"].sum()).round(1)
    return table.head(top_n) if top_n else table

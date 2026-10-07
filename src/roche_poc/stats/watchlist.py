"""Explicit alert rules ("what to watch") and entity ranking.

Every rule is deterministic, uses a threshold from ``config`` and returns a readable
``detail`` string, so each alert can be justified and audited. Rules apply to the
LATEST snapshot of the frame given, using the full history for persistence.
"""

from __future__ import annotations

import pandas as pd

from roche_poc import config
from roche_poc.stats.kpis import is_critical, latest_rows
from roche_poc.stats.persistence import critical_streaks

RULE_ESCALATE = "Escalate: stock-out with production/market impact"
RULE_NO_ROOT_CAUSE = "Governance: critical without root cause"
RULE_NO_COMMENT = "Governance: critical without comment"
RULE_PERSISTENT = "Chronic: critical for many consecutive snapshots"
RULE_RECURRENT = "Recurrent: critical again and again"
RULE_LONG_DELAY = "Delivery: long delay on a critical element"

HIGH, MEDIUM = "high", "medium"
_ID_COLUMNS = [config.COL_MATERIAL, config.COL_MATERIAL_DESC, config.COL_VENDOR, config.COL_MRP]
_OUT_COLUMNS = _ID_COLUMNS + ["rule", "severity", "detail"]


def _flag(rows: pd.DataFrame, rule: str, severity: str, detail) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=_OUT_COLUMNS)
    cols = [c for c in _ID_COLUMNS if c in rows.columns]
    out = rows[cols].copy()
    out["rule"] = rule
    out["severity"] = severity
    out["detail"] = detail(rows) if callable(detail) else detail
    return out


def build_watchlist(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per (material, rule) alert, most severe first."""
    if df.empty:
        return pd.DataFrame(columns=_OUT_COLUMNS)
    now = latest_rows(df)
    critical_now = now[is_critical(now)]
    parts: list[pd.DataFrame] = []

    escalate = critical_now[
        (critical_now[config.COL_STATUS] == config.STATUS_ACTUAL)
        & critical_now[config.COL_IMPACT].isin(config.ESCALATION_IMPACTS)
    ]
    parts.append(
        _flag(escalate, RULE_ESCALATE, HIGH, lambda r: "Actual stock-out, impact " + r[config.COL_IMPACT].astype(str))
    )
    parts.append(
        _flag(
            critical_now[critical_now[config.COL_ROOT_CAUSE].isna()],
            RULE_NO_ROOT_CAUSE, MEDIUM, "No root cause entered although status is critical",
        )
    )
    parts.append(
        _flag(
            critical_now[critical_now[config.COL_COMMENT].isna()],
            RULE_NO_COMMENT, MEDIUM, "No planner comment although status is critical",
        )
    )
    if config.COL_DELAY in critical_now.columns:
        # Assumes ``Delay`` is expressed in days: to be confirmed with the data owner.
        long_delay = critical_now[critical_now[config.COL_DELAY] > config.LONG_DELAY_DAYS]
        parts.append(
            _flag(
                long_delay, RULE_LONG_DELAY, MEDIUM,
                lambda r: "Delay " + r[config.COL_DELAY].round(0).astype(int).astype(str) + " > "
                + str(config.LONG_DELAY_DAYS),
            )
        )

    streaks = critical_streaks(df)
    present_now = set(now[config.COL_MATERIAL])
    persistent = streaks[
        (streaks["current_streak"] >= config.PERSISTENT_CRITICAL_SNAPSHOTS)
        & streaks.index.isin(present_now)
    ]
    recurrent = streaks[
        (streaks["episodes"] >= config.RECURRENT_EPISODES) & streaks.index.isin(present_now)
    ]
    attrs = (
        now.drop_duplicates(config.COL_MATERIAL).set_index(config.COL_MATERIAL)
        [[c for c in _ID_COLUMNS if c != config.COL_MATERIAL and c in now.columns]]
    )
    for table, rule, severity, text in (
        (persistent, RULE_PERSISTENT, HIGH, lambda t: "Critical for " + t["current_streak"].astype(str) + " consecutive snapshots"),
        (recurrent, RULE_RECURRENT, MEDIUM, lambda t: t["episodes"].astype(str) + " separate critical episodes"),
    ):
        if table.empty:
            continue
        frame = table.join(attrs).reset_index().rename(columns={"index": config.COL_MATERIAL})
        frame = frame.rename(columns={frame.columns[0]: config.COL_MATERIAL})
        frame["rule"], frame["severity"], frame["detail"] = rule, severity, text(table).to_numpy()
        parts.append(frame.reindex(columns=_OUT_COLUMNS))

    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame(columns=_OUT_COLUMNS)
    watch = pd.concat(parts, ignore_index=True).drop_duplicates(
        subset=[config.COL_MATERIAL, "rule"]
    )
    watch["_rank"] = watch["severity"].map({HIGH: 0, MEDIUM: 1})
    return watch.sort_values(["_rank", config.COL_MATERIAL]).drop(columns="_rank").reset_index(drop=True)


def rank_entities(df: pd.DataFrame, level: str, watchlist: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rank vendors / MRP controllers / materials by current risk (latest snapshot).

    Columns: critical elements, actual stock-outs, critical share, high-severity alerts.
    Sorted by high alerts, then actual stock-outs, then critical share.
    """
    col = config.LEVEL_COLUMNS[level]
    watchlist = build_watchlist(df) if watchlist is None else watchlist
    now = latest_rows(df)
    crit = is_critical(now)
    base = now.assign(
        _crit=crit, _actual=now[config.COL_STATUS] == config.STATUS_ACTUAL
    ).groupby(col).agg(
        elements=(config.COL_MATERIAL, "size"),
        materials=(config.COL_MATERIAL, "nunique"),
        critical=("_crit", "sum"),
        actual_stockouts=("_actual", "sum"),
        critical_share=("_crit", "mean"),
    )
    if not watchlist.empty and col in watchlist.columns:
        high = watchlist[watchlist["severity"] == HIGH].groupby(col).size()
        base["high_alerts"] = high.reindex(base.index).fillna(0).astype(int)
    else:
        base["high_alerts"] = 0
    base["critical_share"] = base["critical_share"].round(3)
    return base.sort_values(
        ["high_alerts", "actual_stockouts", "critical_share"], ascending=False
    ).reset_index()

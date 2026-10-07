"""Cleaning of raw snapshot rows.

Design rules (they fix the issues found in the first prototype):
* nothing is dropped silently: every step reports how many rows it touched;
* a comment without the ``pseudo, YYYY-MM-DD:`` prefix is KEPT (the former
  ``str.split(": ", n=1).str[1]`` turned it into NaN and deleted it);
* duplicates are removed only when the WHOLE row is identical, so that the
  history of a persisting issue is preserved for the statistics.
"""

from __future__ import annotations

import re

import pandas as pd

from roche_poc import config

# "schera12, 2026-03-02: text"  ->  "text"
_PREFIX_RE = re.compile(r"^\s*[^,:\n]{1,80},\s*\d{4}-\d{2}-\d{2}[^:\n]{0,20}:\s*")
_DATE_COLUMNS = (
    config.COL_SNAPSHOT,
    config.COL_STOCKOUT_DATE,
    "ITEM_DELIVERY_DATE",
    "RESCHEDULING_DATE",
)


def strip_comment_prefix(comments: pd.Series) -> tuple[pd.Series, int]:
    """Remove the leading ``pseudo, date:`` tag when present, keep the text otherwise.

    Returns the cleaned series and the number of comments whose prefix was removed.
    Whitespace (tabs, newlines, double spaces) is collapsed to single spaces.
    """
    text = comments.astype("string")
    has_prefix = text.str.contains(_PREFIX_RE, na=False)
    cleaned = text.str.replace(_PREFIX_RE, "", regex=True)
    cleaned = cleaned.str.replace(r"\s+", " ", regex=True).str.strip()
    cleaned = cleaned.mask(cleaned == "", pd.NA)
    return cleaned, int(has_prefix.sum())


def normalize_impact(value) -> object:
    """Map the free-form impact labels to the four-level scale."""
    if pd.isna(value):
        return pd.NA
    label = str(value).strip().lower()
    if label.startswith("none"):
        return config.IMPACT_NONE
    if label.startswith("logist"):
        return config.IMPACT_LOGISTICS
    if label.startswith("production"):
        return config.IMPACT_PRODUCTION
    if label.startswith("market"):
        return config.IMPACT_MARKET
    return str(value).strip()


def normalize_status(value) -> object:
    """Standardise the SAP material status (``Unknown Status (Good Part)`` -> Good Part)."""
    if pd.isna(value):
        return pd.NA
    label = str(value).strip()
    if label.lower().startswith("unknown status"):
        return config.STATUS_GOOD
    return label


def clean_snapshots(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return the cleaned ``snapshots`` table and a report of what each step did."""
    report: dict = {"rows_in": len(raw)}
    df = raw.rename(columns=config.RAW_RENAMES).copy()

    if config.COL_COMMENT in df.columns:
        df[config.COL_COMMENT], n_prefix = strip_comment_prefix(df[config.COL_COMMENT])
        report["comments_prefix_removed"] = n_prefix
        report["rows_without_comment"] = int(df[config.COL_COMMENT].isna().sum())

    for col in _DATE_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    report["rows_invalid_snapshot_date"] = int(df[config.COL_SNAPSHOT].isna().sum())
    df = df.dropna(subset=[config.COL_SNAPSHOT])

    if config.COL_DELAY in df.columns:
        df[config.COL_DELAY] = pd.to_numeric(df[config.COL_DELAY], errors="coerce")
    if config.COL_STATUS in df.columns:
        df[config.COL_STATUS + "_RAW"] = df[config.COL_STATUS]
        df[config.COL_STATUS] = df[config.COL_STATUS].map(normalize_status)
    if config.COL_IMPACT in df.columns:
        df[config.COL_IMPACT] = df[config.COL_IMPACT].map(normalize_impact)

    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    report["rows_exact_duplicates_removed"] = before - len(df)
    report["rows_out"] = len(df)
    report["n_snapshots"] = int(df[config.COL_SNAPSHOT].nunique())
    return df, report

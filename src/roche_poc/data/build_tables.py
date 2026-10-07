"""Build the two core tables from the cleaned snapshots.

``snapshots``  one row per (snapshot, MRP element): basis of ALL statistics
``comments``   one row per unique (material, comment): basis of NLP and LLM

Keeping both grains avoids the bias of the first prototype, where statistics
were computed on de-duplicated comments only (a comment persisting over ten
weeks counted once, which produced an artificial -91 % "trend").
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from roche_poc import config
from roche_poc.data.cleaning import clean_snapshots
from roche_poc.data.loading import load_raw_snapshots

log = logging.getLogger(__name__)

_LAST_VALUE_COLUMNS = (
    config.COL_ROOT_CAUSE,
    config.COL_IMPACT,
    config.COL_STATUS,
    config.COL_VENDOR,
    config.COL_MRP,
    config.COL_MATERIAL_DESC,
)


def build_comments_table(snapshots: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to one row per unique (material, comment) with its lifetime."""
    has_comment = snapshots[config.COL_COMMENT].notna()
    base = snapshots.loc[has_comment].sort_values(config.COL_SNAPSHOT)
    keys = [config.COL_MATERIAL, config.COL_COMMENT]
    aggregations = {
        "first_seen": (config.COL_SNAPSHOT, "min"),
        "last_seen": (config.COL_SNAPSHOT, "max"),
        "n_snapshots": (config.COL_SNAPSHOT, "nunique"),
    }
    for col in _LAST_VALUE_COLUMNS:
        if col in base.columns:
            aggregations[col] = (col, "last")  # last non-null value in time order
    return base.groupby(keys, dropna=False).agg(**aggregations).reset_index()


def save_table(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Build it first: python -m roche_poc.data.build_tables"
        )
    return pd.read_parquet(path)


def build_all(raw_dir: Path | str = config.RAW_DIR) -> dict:
    """Run loading -> cleaning -> tables, save to ``data/processed/`` and return the report."""
    raw = load_raw_snapshots(raw_dir)
    snapshots, report = clean_snapshots(raw)
    comments = build_comments_table(snapshots)
    report["unique_comments"] = len(comments)
    save_table(snapshots, config.SNAPSHOTS_PATH)
    save_table(comments, config.COMMENTS_PATH)
    log.info("Build report: %s", report)
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for key, value in build_all().items():
        print(f"{key:35s} {value}")

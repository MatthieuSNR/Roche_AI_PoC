"""Synthetic fixtures (NO Roche data): 8 weekly snapshots, 6 materials, crafted so that
each watchlist rule has exactly one known trigger."""

from __future__ import annotations

import pandas as pd

from roche_poc import config

SNAPSHOTS = pd.date_range("2026-03-02", periods=8, freq="7D")
G, B, P, A = config.STATUS_GOOD, config.STATUS_BELOW_SAFETY, config.STATUS_POTENTIAL, config.STATUS_ACTUAL


def _rows(material, vendor, mrp, statuses, impact=None, cause=None, comment=None, delay=0.0):
    rows = []
    for date, status in zip(SNAPSHOTS, statuses):
        if status is None:  # material absent from this snapshot
            continue
        rows.append(
            {
                config.COL_SNAPSHOT: date,
                config.COL_MATERIAL: material,
                config.COL_MATERIAL_DESC: f"Part {material}",
                config.COL_VENDOR: vendor,
                config.COL_MRP: mrp,
                config.COL_STATUS: status,
                config.COL_IMPACT: impact if status in (P, A) else config.IMPACT_NONE,
                config.COL_ROOT_CAUSE: cause if status in (P, A) else None,
                config.COL_COMMENT: comment if status in (P, A) else None,
                config.COL_STOCKOUT_DATE: date + pd.Timedelta(days=10) if status == A else pd.NaT,
                config.COL_DELAY: delay,
            }
        )
    return rows


def make_snapshots() -> pd.DataFrame:
    rows = []
    # 1: Actual stock-out for 8 snapshots, production impact, NO root cause, NO comment
    rows += _rows(1, "Vendor A", "M1", [A] * 8, impact=config.IMPACT_PRODUCTION)
    # 2: three separate critical episodes, critical again at the last snapshot (streak 1)
    rows += _rows(2, "Vendor A", "M1", [P, P, G, G, P, P, G, P], impact=config.IMPACT_LOGISTICS,
                  cause="S_Lack of Raw Material", comment="Waiting for raw material")
    # 3: always good
    rows += _rows(3, "Vendor B", "M2", [G] * 8)
    # 4: below safety only (warning, not critical)
    rows += _rows(4, "Vendor B", "M2", [B] * 8)
    # 5: potential stock-out on the last 2 snapshots, documented, long delay
    rows += _rows(5, "Vendor C", "M2", [G] * 6 + [P, P], impact=config.IMPACT_LOGISTICS,
                  cause="PL_Shortterm demand", comment="Demand peak", delay=20.0)
    # 6: only present in the first 3 snapshots (absent from the latest one)
    rows += _rows(6, "Vendor C", "M2", [A, A, A] + [None] * 5, impact=config.IMPACT_MARKET,
                  cause="S_Quality Failed Finished Goods", comment="Quality issue")
    return pd.DataFrame(rows)


def make_comments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {config.COL_MATERIAL: 2, config.COL_COMMENT: "Waiting for raw material",
             config.COL_VENDOR: "Vendor A", config.COL_MRP: "M1",
             "first_seen": SNAPSHOTS[0], "last_seen": SNAPSHOTS[7], "n_snapshots": 5,
             config.COL_ROOT_CAUSE: "S_Lack of Raw Material", config.COL_IMPACT: "Logistics"},
            {config.COL_MATERIAL: 5, config.COL_COMMENT: "Demand peak",
             config.COL_VENDOR: "Vendor C", config.COL_MRP: "M2",
             "first_seen": SNAPSHOTS[6], "last_seen": SNAPSHOTS[7], "n_snapshots": 2,
             config.COL_ROOT_CAUSE: "PL_Shortterm demand", config.COL_IMPACT: "Logistics"},
        ]
    )

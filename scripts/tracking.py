"""
Item tracking table: data/item_tracking.csv, built from ALL the snapshot rows, not only the commented ones.

cleaned_comments.csv keeps one row per comment, so a root cause or an impact entered without a comment is
lost (2,218 rows with a root cause, 1,889 with an impact). This table keeps them, for the analyses over time
of the dashboard sections Root Cause Trends, Impact by Root Cause and Weak Signals (scripts/insights.py):

  one row per (snapshot day, material, vendor) = an "item" on a day, when on that day the item has a
  root cause, an impact, a comment, or the status Actual / Potential Stock Out.

A material has several order lines per day (up to 70): they are summarised per item and day as
  MATERIAL_STATUS  the worst status of the lines (Actual > Potential > Below Safety > Good Part),
  Root_Cause       a root cause entered on one of the lines,
  Impact_Level     the most severe impact entered (Market > Production > Logistics > None (no impact));
                   empty = impact not communicated (which does not mean that there is no impact),
  Comment          the comment, cleaned like in cleaned_comments.csv (entries split, logins removed),
  N_Lines          the number of order lines.
No login and no free text other than the cleaned comment is kept.

Usage (from the project root):  python scripts/tracking.py      (~40 s, reads every snapshot)
"""

import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_cleaning as dc  # noqa: E402

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKING_PATH = os.path.join(project_dir, "data", "item_tracking.csv")

ITEM = ["MATERIAL_NUMBER", "VENDOR_ACCOUNT_NUMBER"]
STATUS_RANK = {"Actual Stock Out": 0, "Potential Stock Out": 1, "Below Safety": 2, "Good Part": 3,
               "Unknown Status (Good Part)": 4}
# The data holds two spellings per impact level ("Production" and "Production (Stop&Go/...)")
# "None (no impact)" = the planner entered that there is no impact (ION label; "None" alone would be read back
# from the CSV as a missing value). An empty impact means "not communicated", never "no impact".
IMPACT_LEVELS = ["Market", "Production", "Logistics", "None (no impact)"]   # most severe first
IMPACT_PREFIXES = {"market": "Market", "production": "Production", "logistic": "Logistics", "none": "None (no impact)"}
SEVERE_IMPACTS = {"Market", "Production"}


def impact_level(value):
    """'Production (Stop&Go/Stock out on the production line)' -> 'Production'; NaN stays NaN."""
    if pd.isna(value):
        return None
    label = str(value).strip().lower()
    return next((level for prefix, level in IMPACT_PREFIXES.items() if label.startswith(prefix)), str(value).strip())


def build_tracking(merged):
    """One row per (snapshot day, material, vendor) with a root cause, an impact, a comment or a stock-out status."""
    stock_out = merged["MATERIAL_STATUS"].isin(["Actual Stock Out", "Potential Stock Out"])
    df = merged[merged[["Root_Cause", "Impact", "Comment"]].notna().any(axis=1) | stock_out].copy()

    cleaned = {c: dc.clean_comment(c) for c in df["Comment"].dropna().unique()}   # each distinct cell once
    df["Comment"] = df["Comment"].map(cleaned)
    df["Impact_Level"] = df["Impact"].map(impact_level)
    df["_status"] = df["MATERIAL_STATUS"].map(STATUS_RANK).fillna(9)
    df["_impact"] = df["Impact_Level"].map({level: i for i, level in enumerate(IMPACT_LEVELS)}).fillna(9)

    key = ["Snapshot_Date"] + ITEM
    # worst status first, then most severe impact: "first" of each group is the value to keep
    df = df.sort_values(key + ["_status", "_impact"], kind="stable")
    grouped = df.groupby(key, sort=False, dropna=False)
    out = grouped.agg(
        MATERIAL_STATUS=("MATERIAL_STATUS", "first"), Root_Cause=("Root_Cause", "first"),
        Comment=("Comment", "first"), VENDOR_NAME=("VENDOR_NAME", "first"),
        MATERIAL_DESC=("MATERIAL_DESC", "first"), MRP_CONTROLLER=("MRP_CONTROLLER", "first"),
        PURCHASING_GROUP=("PURCHASING_GROUP", "first"), PLANT=("PLANT", "first"), N_Lines=("Snapshot_Date", "size"),
    )
    impact = df.sort_values(key + ["_impact"], kind="stable").groupby(key, sort=False, dropna=False)["Impact_Level"].first()
    out = out.join(impact).reset_index()
    return out.sort_values(key, kind="stable").reset_index(drop=True)


if __name__ == "__main__":
    started = time.time()
    merged = dc.merge_snapshots()
    tracking = build_tracking(merged)
    tracking.to_csv(TRACKING_PATH, index=False)
    items = tracking.groupby(ITEM).ngroups
    print(f"{merged.attrs['n_files']} files, {len(merged):,} rows -> {len(tracking):,} item-days, {items:,} items "
          f"({time.time() - started:.0f} s)")
    print(f"with a root cause: {tracking['Root_Cause'].notna().sum():,} | an impact: {tracking['Impact_Level'].notna().sum():,} "
          f"| a comment: {tracking['Comment'].notna().sum():,}")
    print(f"✅ Saved to {TRACKING_PATH}")

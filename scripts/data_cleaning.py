"""
Data cleaning: builds data/cleaned_comments.csv from the daily snapshots in data/Snapshot_2026/.

One row per unique (material, vendor, comment). A comment stays in the dashboard for many
days, so instead of keeping only its first appearance we record how long it was visible:
First_Seen, Last_Seen, N_Snapshots (number of daily snapshots showing it) and Days_Active.
The other columns (status, root cause, impact...) take their latest known value.

Usage (from the project root):  python scripts/data_cleaning.py
Then translate the German comments: python scripts/translation.py
"""

import glob
import os
import re

import pandas as pd

# Paths (relative to the project root, so the script works from any folder)
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_DIR = os.path.join(project_dir, "data", "Snapshot_2026")
OUTPUT_PATH = os.path.join(project_dir, "data", "cleaned_comments.csv")

# Columns kept in cleaned_comments.csv (same list as before + the persistence columns)
USEFUL_COLUMNS = [
    "Snapshot_Date", "MATERIAL_NUMBER", "PLANT", "MRP_CONTROLLER",
    "MATERIAL_DESC", "RESCHEDULING_DATE", "VENDOR_ACCOUNT_NUMBER",
    "VENDOR_NAME", "ITEM_DELIVERY_DATE", "PO_QTY", "INVENTORY_QTY",
    "STOCKOUT_DATE", "BLOCKED_STOCK", "QUALITY_INSPECTION_STOCK",
    "ORDER_CONFIRMATION", "PURCHASING_GROUP", "SOURCING_MANAGER",
    "Delay", "Horizon", "Total", "MATERIAL_STATUS", "MATERIAL_RISK",
    "Comment", "Root_Cause", "Impact", "Instruments_Affected",
]
PERSISTENCE_COLUMNS = ["First_Seen", "Last_Seen", "N_Snapshots", "Days_Active"]

# Planner prefix written by the tool: "pseudo, 2026-06-18: actual comment"
PREFIX_PATTERN = re.compile(r"^\s*[^,:]{1,40},\s*\d{4}-\d{2}-\d{2}:\s*")


def clean_comment(text):
    """Remove the 'pseudo, YYYY-MM-DD: ' prefix and normalise whitespace.
    Comments without prefix are kept as they are (the old split on ': ' dropped them)."""
    if pd.isna(text):
        return None
    text = PREFIX_PATTERN.sub("", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def load_commented_rows(snapshot_dir=SNAPSHOT_DIR):
    """Read every snapshot CSV and keep only the rows that carry a comment."""
    files = sorted(glob.glob(os.path.join(snapshot_dir, "*.csv")))
    if not files:
        raise FileNotFoundError(f"No snapshot CSV found in {snapshot_dir}")
    parts = []
    for file in files:
        df = pd.read_csv(file, low_memory=False)
        parts.append(df[df["comment"].notna()])
    df = pd.concat(parts, ignore_index=True)
    return df.rename(columns={"Issue": "Root_Cause", "comment": "Comment"})


def build_cleaned_comments(raw):
    """One row per (material, vendor, comment) with its persistence over the snapshots."""
    df = raw.copy()
    df["Comment"] = df["Comment"].map(clean_comment)
    df = df.dropna(subset=["Comment"])
    df["Snapshot_Date"] = pd.to_datetime(df["Snapshot_Date"], errors="coerce")
    df = df.dropna(subset=["Snapshot_Date"]).sort_values("Snapshot_Date")

    key = ["MATERIAL_NUMBER", "VENDOR_ACCOUNT_NUMBER", "Comment"]
    grouped = df.groupby(key, dropna=False, sort=False)

    # Latest known value of each column (last() skips missing values, so a root cause
    # filled in later is kept even if the very last row is empty)
    latest = grouped.last()
    persistence = grouped["Snapshot_Date"].agg(First_Seen="min", Last_Seen="max", N_Snapshots="nunique")
    out = latest.join(persistence).reset_index()
    out["Days_Active"] = (out["Last_Seen"] - out["First_Seen"]).dt.days + 1
    out["Snapshot_Date"] = out["Last_Seen"]

    out = out[USEFUL_COLUMNS + PERSISTENCE_COLUMNS]
    return out.sort_values(["Last_Seen", "MATERIAL_NUMBER"], ascending=[False, True]).reset_index(drop=True)


if __name__ == "__main__":
    raw = load_commented_rows()
    cleaned = build_cleaned_comments(raw)
    print(f"Snapshots: {raw['Snapshot_Date'].nunique()} | commented rows: {len(raw)}")
    print(f"Unique comments (material, vendor, comment): {len(cleaned)}")
    print(f"Distinct comment texts: {cleaned['Comment'].nunique()}")

    cleaned.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved to {OUTPUT_PATH}")
    print("Next step: python scripts/translation.py (adds comment_language and Comment_EN)")

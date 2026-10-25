"""
Data cleaning: builds data/cleaned_comments.csv from the daily snapshots in data/Snapshot_2026/.

One row per unique (material, vendor, comment). A comment stays in the dashboard for many
days, so instead of keeping only its first appearance we record how long it was visible:
First_Seen, Last_Seen, N_Snapshots (number of daily snapshots showing it) and Days_Active.
The other columns (status, root cause, impact...) take their latest known value.

A comment cell is a JOURNAL: the tool writes one entry per line, each signed and dated
("login, 2026-06-18: message"), and re-signs an entry every time it is edited, which gives
chains like "hochwall, 2026-07-16: hochwall, 2026-07-13: ellmersl, 2026-06-26: message".
Cleaning therefore works entry by entry (parse_comment):
  1. split the cell into entries (one per signed line; unsigned lines continue the previous entry),
  2. remove the whole signature chain of each entry (login, date, time): the logins are staff
     identifiers, i.e. personal data that must neither stay in the text nor be sent to a cloud
     service (thesis 3.7); only anonymous metadata is kept (number of entries, number of
     distinct authors, first and last entry date),
  3. write the entries one per line in the same cell, so that the succession of entries stays
     visible: "Comment" (original wording) and "Comment_Expanded" (abbreviations written out,
     scripts/abbreviations.py + lexicon/abbreviations.csv).
Next steps of the pipeline (scripts/translation.py): pseudonymise -> DeepL, entry by entry.

Usage (from the project root):  python scripts/data_cleaning.py
Then translate the German comments: python scripts/translation.py
"""

import glob
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # translation.py, abbreviations.py

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
# Anonymous metadata of the journal (the authors themselves are not kept)
ENTRY_COLUMNS = ["N_Entries", "N_Authors", "First_Entry_Date", "Last_Entry_Date", "Entry_Languages"]
ENTRY_SEPARATOR = "\n"   # one entry per line inside the cell

# Signature written by the tool in front of every entry: "login, 2026-06-18: " (optionally with a time).
# Logins look like hottlerj, peralta4, schera12. Dates seen in the data: ISO (2026-06-18) and, by
# typing mistakes, "20206-07-23" or "08072026" (DDMMYYYY): the signature is removed in all cases.
LOGIN = r"[A-Za-z][A-Za-z0-9_.\-]{1,20}"
SIGNATURE = re.compile(
    rf"^\s*(?P<author>{LOGIN})\s*,\s*(?P<date>\d{{4,5}}-\d{{1,2}}-\d{{1,2}}|\d{{8}})"
    rf"(?:[ T]+(?P<time>\d{{1,2}}:\d{{2}}(?::\d{{2}})?))?(?:\s*:\s*|\s+)"   # colon sometimes forgotten
)
# A signature in the middle of a line (a new entry typed after text) also opens a new entry
INLINE_SIGNATURE = re.compile(rf"(?<=\S)[ \t]+(?={LOGIN}\s*,\s*\d{{4,5}}-\d{{1,2}}-\d{{1,2}}\s*:)")
MAX_CHAIN = 10  # safety limit for chains of signatures


def parse_entry_date(text):
    """'2026-06-18' -> Timestamp; tolerates '20206-07-23' (typo) and '08072026' (DDMMYYYY); else NaT."""
    text = str(text)
    if re.fullmatch(r"\d{8}", text):
        return pd.to_datetime(text, format="%d%m%Y", errors="coerce")
    year, rest = text.split("-", 1)
    if len(year) == 5:                       # 20206 -> 2026: drop the character that makes it plausible
        year = next((c for c in (year[:i] + year[i + 1:] for i in range(5)) if 2020 <= int(c) <= 2035), year)
    return pd.to_datetime(f"{year}-{rest}", format="%Y-%m-%d", errors="coerce")


def _squeeze(text):
    return re.sub(r"\s+", " ", text).strip()


def split_entries(raw):
    """Split a comment cell into entries: [{'authors': [...], 'dates': [...], 'text': str}].
    A line starting with a signature opens a new entry; a line without signature (a pasted SAP
    line, a second sentence) continues the previous entry. Entries without text are dropped."""
    entries = []
    for line in re.split(r"\r\n|\r|\n", INLINE_SIGNATURE.sub("\n", str(raw))):
        if not line.strip():
            continue
        authors, dates, rest = [], [], line
        while len(authors) < MAX_CHAIN:
            m = SIGNATURE.match(rest)
            if not m:
                break
            authors.append(m.group("author"))
            dates.append(parse_entry_date(m.group("date")))
            rest = rest[m.end():]
        text = _squeeze(rest)
        if authors or not entries:
            entries.append({"authors": authors, "dates": dates, "text": text})
        else:  # continuation of the previous entry
            entries[-1]["text"] = _squeeze(entries[-1]["text"] + " " + text)
    # An entry that is only a signature (chain "a, date: b, date: text" split at the inline signatures)
    # hands its authors and dates over to the entry that follows it
    merged, carry_authors, carry_dates = [], [], []
    for e in entries:
        if not e["text"]:
            carry_authors, carry_dates = carry_authors + e["authors"], carry_dates + e["dates"]
            continue
        merged.append({"authors": carry_authors + e["authors"], "dates": carry_dates + e["dates"], "text": e["text"]})
        carry_authors, carry_dates = [], []
    return merged


def parse_comment(raw):
    """Entries of a comment cell and their anonymous metadata (None if there is no text).
    Outermost signature = last time the entry was saved; innermost = when it was first written."""
    if pd.isna(raw):
        return None
    entries = split_entries(raw)
    if not entries:
        return None
    first = [e["dates"][-1] for e in entries if e["dates"]]
    last = [e["dates"][0] for e in entries if e["dates"]]
    return {
        "entries": [e["text"] for e in entries],
        "comment": ENTRY_SEPARATOR.join(e["text"] for e in entries),
        "n_entries": len(entries),
        "n_authors": len({a.lower() for e in entries for a in e["authors"]}),
        "first_entry_date": pd.Series(first, dtype="datetime64[ns]").min() if first else pd.NaT,
        "last_entry_date": pd.Series(last, dtype="datetime64[ns]").max() if last else pd.NaT,
    }


def clean_comment(text):
    """Comment without signatures, one entry per line (None if empty). Kept for the notebooks."""
    parsed = parse_comment(text)
    return parsed["comment"] if parsed else None


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


def build_cleaned_comments(raw, expand=True):
    """One row per (material, vendor, comment) with its persistence over the snapshots.
    expand=True also writes Comment_Expanded (abbreviations written out)."""
    df = raw.copy()
    parsed = {c: parse_comment(c) for c in df["Comment"].dropna().unique()}   # each distinct cell once
    df["_parsed"] = df["Comment"].map(parsed)
    df = df.dropna(subset=["_parsed"]).copy()
    df["Comment"] = df["_parsed"].map(lambda p: p["comment"])
    df["N_Entries"] = df["_parsed"].map(lambda p: p["n_entries"])
    df["N_Authors"] = df["_parsed"].map(lambda p: p["n_authors"])
    df["First_Entry_Date"] = pd.to_datetime(df["_parsed"].map(lambda p: p["first_entry_date"]))
    df["Last_Entry_Date"] = pd.to_datetime(df["_parsed"].map(lambda p: p["last_entry_date"]))
    df = df.drop(columns="_parsed")
    df["Snapshot_Date"] = pd.to_datetime(df["Snapshot_Date"], errors="coerce")
    df = df.dropna(subset=["Snapshot_Date"]).sort_values("Snapshot_Date")

    key = ["MATERIAL_NUMBER", "VENDOR_ACCOUNT_NUMBER", "Comment"]
    grouped = df.groupby(key, dropna=False, sort=False)

    # Latest known value of each column (last() skips missing values, so a root cause
    # filled in later is kept even if the very last row is empty)
    latest = grouped.last().drop(columns=["First_Entry_Date", "Last_Entry_Date"])
    persistence = grouped["Snapshot_Date"].agg(First_Seen="min", Last_Seen="max", N_Snapshots="nunique")
    entry_dates = grouped.agg(First_Entry_Date=("First_Entry_Date", "min"), Last_Entry_Date=("Last_Entry_Date", "max"))
    out = latest.join(persistence).join(entry_dates).reset_index()
    out["Days_Active"] = (out["Last_Seen"] - out["First_Seen"]).dt.days + 1
    out["Snapshot_Date"] = out["Last_Seen"]

    # Language of each entry (needed to choose the right expansion) and abbreviations written out
    from translation import detect_language
    unique = out["Comment"].unique()
    languages = {c: [detect_language(e) for e in c.split(ENTRY_SEPARATOR)] for c in unique}
    out["Entry_Languages"] = out["Comment"].map(lambda c: "|".join(languages[c]))
    columns = USEFUL_COLUMNS
    if expand:
        from abbreviations import expand_comment, load_library
        library = load_library()
        expanded = {c: expand_comment(c, languages[c], library) for c in unique}
        out["Comment_Expanded"] = out["Comment"].map(expanded)
        columns = columns + ["Comment_Expanded"]

    out = out[columns + PERSISTENCE_COLUMNS + ENTRY_COLUMNS]
    return out.sort_values(["Last_Seen", "MATERIAL_NUMBER"], ascending=[False, True]).reset_index(drop=True)


if __name__ == "__main__":
    raw = load_commented_rows()
    cleaned = build_cleaned_comments(raw)
    print(f"Snapshots: {raw['Snapshot_Date'].nunique()} | commented rows: {len(raw)}")
    print(f"Unique comments (material, vendor, comment): {len(cleaned)}")
    print(f"Distinct comment texts: {cleaned['Comment'].nunique()}")
    print(f"Comments with several entries: {(cleaned['N_Entries'] > 1).sum()} "
          f"(max {cleaned['N_Entries'].max()} entries) | entries in total: {cleaned['N_Entries'].sum()}")

    cleaned.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved to {OUTPUT_PATH}")
    print("Next step: python scripts/translation.py (pseudonymises, translates entry by entry: adds Comment_EN)")

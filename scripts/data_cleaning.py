"""
Data cleaning: builds data/cleaned_comments.csv from the daily snapshots in data/Snapshot_2026/.

The cleaning is a sequence of small steps, each one a function that takes a table and returns a table,
so that every step can be run and checked on its own in scripts/data_cleaning.ipynb:

  1. merge_snapshots        assemble the weekly snapshot CSV files into one table
  2. keep_commented_rows    keep the rows that carry a comment
  3. split_journal          cut each comment cell into its entries, remove login + date + time
  4. deduplicate_comments   one row per (material, vendor, comment) + persistence over the snapshots
  5. detect_languages       language (de / en) of every entry
  6. expand_abbreviations   write the certain abbreviations out, according to the language of the entry
  then scripts/translation.py: 7. pseudonymise -> DeepL (with glossary and cache), entry by entry.

A comment cell is a JOURNAL: the tool writes one entry per line, each signed and dated
("login, 2026-06-18: message"), and re-signs an entry every time it is edited, which gives
chains like "hochwall, 2026-07-16: hochwall, 2026-07-13: ellmersl, 2026-06-26: message".
Step 3 therefore works entry by entry (parse_comment):
  * an entry starts at each signature; unsigned lines continue the previous entry,
  * the whole signature chain is removed: logins are staff identifiers, i.e. personal data that must
    neither stay in the text nor be sent to a cloud service (thesis 3.7); only anonymous metadata is
    kept (number of entries, number of distinct authors, first and last entry date),
  * the entries are written one after the other in the same cell, separated by " ¦▸ " (scripts/entries.py),
    so that the succession of entries stays visible.
"Comment" keeps the original wording, "Comment_Expanded" has the abbreviations written out
(scripts/abbreviations.py + lexicon/abbreviations.csv).

One row per unique (material, vendor, comment). A comment stays in the dashboard for many days, so
instead of keeping only its first appearance we record how long it was visible: First_Seen, Last_Seen,
N_Snapshots and Days_Active. The other columns (status, root cause, impact...) take their latest known value.

Usage (from the project root):  python scripts/data_cleaning.py
Then translate the German comments: python scripts/translation.py
"""

import glob
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # translation.py, abbreviations.py

from entries import ENTRY_SEPARATOR, join_entries, split_cell  # noqa: E402

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
        "comment": join_entries(e["text"] for e in entries),
        "n_entries": len(entries),
        "n_authors": len({a.lower() for e in entries for a in e["authors"]}),
        "first_entry_date": pd.Series(first, dtype="datetime64[ns]").min() if first else pd.NaT,
        "last_entry_date": pd.Series(last, dtype="datetime64[ns]").max() if last else pd.NaT,
    }


def clean_comment(text):
    """Comment without signatures, entries joined by ENTRY_SEPARATOR (None if empty). Kept for the notebooks."""
    parsed = parse_comment(text)
    return parsed["comment"] if parsed else None


def describe_step(label, before, after):
    """One line for the log / the notebook: rows before and after a step."""
    return f"{label}: {len(before):,} -> {len(after):,} rows ({len(after) - len(before):+,})"


# ------------------------------------------------------------------ step 1
def merge_snapshots(snapshot_dir=SNAPSHOT_DIR, commented_only=False):
    """STEP 1. Assemble the snapshot CSV files into one table (Issue is renamed Root_Cause, comment Comment).
    commented_only=True keeps only the commented rows while reading (less memory); the number of rows
    read is then given in table.attrs['rows_total'], the number of files in table.attrs['n_files']."""
    files = sorted(glob.glob(os.path.join(snapshot_dir, "*.csv")))
    if not files:
        raise FileNotFoundError(f"No snapshot CSV found in {snapshot_dir}")
    parts, total = [], 0
    for file in files:
        df = pd.read_csv(file, low_memory=False)
        total += len(df)
        parts.append(df[df["comment"].notna()] if commented_only else df)
    df = pd.concat(parts, ignore_index=True).rename(columns={"Issue": "Root_Cause", "comment": "Comment"})
    df.attrs.update(rows_total=total, n_files=len(files))
    return df


# ------------------------------------------------------------------ step 2
def keep_commented_rows(df):
    """STEP 2. Keep the rows with a comment (not empty, not only spaces)."""
    comment = df["Comment"]
    return df[comment.notna() & (comment.astype(str).str.strip() != "")].copy()


# ------------------------------------------------------------------ step 3
def split_journal(df, keep_raw=False):
    """STEP 3. Cut every comment cell into its entries and remove the signatures.
    Comment = entries joined by ENTRY_SEPARATOR; adds N_Entries, N_Authors, First_Entry_Date, Last_Entry_Date.
    Rows whose comment is only a signature are dropped. keep_raw=True keeps the cell as written in
    Comment_Raw (it contains the logins: for checking in the notebook only, never saved)."""
    df = df.copy()
    parsed = {c: parse_comment(c) for c in df["Comment"].dropna().unique()}   # each distinct cell once
    df["_parsed"] = df["Comment"].map(parsed)
    if keep_raw:
        df["Comment_Raw"] = df["Comment"]
    df = df.dropna(subset=["_parsed"]).copy()
    df["Comment"] = df["_parsed"].map(lambda p: p["comment"])
    df["N_Entries"] = df["_parsed"].map(lambda p: p["n_entries"])
    df["N_Authors"] = df["_parsed"].map(lambda p: p["n_authors"])
    df["First_Entry_Date"] = pd.to_datetime(df["_parsed"].map(lambda p: p["first_entry_date"]))
    df["Last_Entry_Date"] = pd.to_datetime(df["_parsed"].map(lambda p: p["last_entry_date"]))
    return df.drop(columns="_parsed")


# ------------------------------------------------------------------ step 4
def deduplicate_comments(df):
    """STEP 4. One row per (material, vendor, comment) with its persistence over the snapshots
    (First_Seen, Last_Seen, N_Snapshots, Days_Active). Other columns: latest known value."""
    df = df.copy()
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
    return out


# ------------------------------------------------------------------ step 5
def detect_languages(df):
    """STEP 5. Language ('de' / 'en') of every entry, detected on the original wording
    (restricted to English / German, see translation.detect_language). Entry_Languages = "de|en|de"."""
    from translation import detect_language
    df = df.copy()
    languages = {c: [detect_language(e) for e in split_cell(c)] for c in df["Comment"].unique()}
    df["Entry_Languages"] = df["Comment"].map(lambda c: "|".join(languages[c]))
    return df


# ------------------------------------------------------------------ step 6
def expand_abbreviations(df):
    """STEP 6. Comment_Expanded = Comment with the certain abbreviations written out
    (lexicon/abbreviations.csv: expand = yes and confidence = high), in the language of each entry."""
    from abbreviations import expand_comment, load_library
    df = df.copy()
    library = load_library()
    languages = df.drop_duplicates("Comment").set_index("Comment")["Entry_Languages"].str.split("|").to_dict()
    expanded = {c: expand_comment(c, languages[c], library) for c in languages}
    df["Comment_Expanded"] = df["Comment"].map(expanded)
    return df


def select_output_columns(df):
    columns = USEFUL_COLUMNS + (["Comment_Expanded"] if "Comment_Expanded" in df.columns else [])
    out = df[columns + PERSISTENCE_COLUMNS + ENTRY_COLUMNS]
    return out.sort_values(["Last_Seen", "MATERIAL_NUMBER"], ascending=[False, True]).reset_index(drop=True)


def load_commented_rows(snapshot_dir=SNAPSHOT_DIR):
    """Steps 1 + 2: every snapshot read, only the rows that carry a comment kept."""
    return keep_commented_rows(merge_snapshots(snapshot_dir, commented_only=True))


def build_cleaned_comments(raw, expand=True):
    """Steps 3 to 6 on the commented rows: the table written to cleaned_comments.csv."""
    df = split_journal(keep_commented_rows(raw))
    df = detect_languages(deduplicate_comments(df))
    if expand:
        df = expand_abbreviations(df)
    return select_output_columns(df)


if __name__ == "__main__":
    merged = merge_snapshots(commented_only=True)
    raw = keep_commented_rows(merged)
    print(f"1. merge_snapshots: {merged.attrs['n_files']} files, {merged.attrs['rows_total']:,} rows in total")
    print(f"2. keep_commented_rows: {len(raw):,} rows with a comment, snapshots: {raw['Snapshot_Date'].nunique()}")
    split = split_journal(raw)
    print(describe_step("3. split_journal (signature-only comments dropped)", raw, split))
    unique = deduplicate_comments(split)
    print(describe_step("4. deduplicate_comments (material, vendor, comment)", split, unique))
    unique = detect_languages(unique)
    print("5. detect_languages (entries):", pd.Series([l for v in unique["Entry_Languages"] for l in v.split("|")]).value_counts().to_dict())
    unique = expand_abbreviations(unique)
    print(f"6. expand_abbreviations: {(unique['Comment'] != unique['Comment_Expanded']).sum():,} comments changed")
    cleaned = select_output_columns(unique)
    print(f"Distinct comment texts: {cleaned['Comment'].nunique()}")
    print(f"Comments with several entries: {(cleaned['N_Entries'] > 1).sum()} "
          f"(max {cleaned['N_Entries'].max()} entries) | entries in total: {cleaned['N_Entries'].sum()}")

    cleaned.to_csv(OUTPUT_PATH, index=False)
    print(f"✅ Saved to {OUTPUT_PATH}")
    print("Next step: python scripts/translation.py (7. pseudonymises, translates entry by entry: adds Comment_EN)")

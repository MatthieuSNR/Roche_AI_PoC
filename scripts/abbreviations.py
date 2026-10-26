"""
Library of abbreviations used in the planner comments (German and English).

* The library is the CSV file lexicon/abbreviations.csv: one row per abbreviation, with a proposed
  meaning in German and English, its context (material planning, production planning, quality...),
  a confidence level and an `expand` flag. Only rows with expand = yes are written out in the text:
  these are the ones whose meaning is certain. The others (ambiguous, unknown, names of companies or
  products) stay untouched until the planners have confirmed them: change `expand` to yes and
  re-run scripts/data_cleaning.py.
* expand_comment() writes the abbreviations of a comment out, entry by entry, in the language of each
  entry ("50 Stk." -> "50 Stück.", "Vorzug KW34" -> "Vorzug Kalenderwoche 34").
  This runs BEFORE pseudonymisation and translation, so that DeepL receives full words.

Matching rules
  exact       case-sensitive ("AB" = Auftragsbestätigung, but not the German word "ab")
  ignore_case "Stk", "STK", "stk"
  exact_dot   case-sensitive and the full stop is required ("u." = und, not the letter u)
  regex       the `pattern` column is used as it is (numbers, dates; \\1 in the expansion = group 1)
  An abbreviation never matches inside a longer word. A full stop that belongs to the abbreviation
  ("ca.", "bzw.", "50 Stk. in Klärung") is consumed; one that ends a sentence ("... 50 Stk. Lieferung")
  is kept.

Usage (from the project root):
  python scripts/abbreviations.py --check      validates the library
  python scripts/abbreviations.py --sheet      writes data/interim/abbreviations_for_review.xlsx (sheet for the planners)
  python scripts/abbreviations.py --report     on demand: data/interim/abbreviations_review.csv (frequencies and
                                               examples, CONFIDENTIAL: to share with the planners, not to push)
  python scripts/abbreviations.py --discover   lists abbreviation-like words that are not in the library yet
  (--sheet, --report and --discover read data/cleaned_comments.csv, or another file given with --comments PATH)
"""

import os
import re
import sys
from dataclasses import dataclass

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from entries import join_entries, split_cell  # noqa: E402

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_PATH = os.path.join(project_dir, "lexicon", "abbreviations.csv")
REVIEW_PATH = os.path.join(project_dir, "data", "interim", "abbreviations_review.csv")
EVIDENCE_PATH = os.path.join(project_dir, "data", "interim", "abbreviation_evidence.csv")
SHEET_PATH = os.path.join(project_dir, "data", "interim", "abbreviations_for_review.xlsx")
COMMENTS_PATH = os.path.join(project_dir, "data", "cleaned_comments.csv")

MATCH_TYPES = {"exact", "ignore_case", "exact_dot", "regex"}
LETTERS = "A-Za-zÄÖÜäöüß"
REQUIRED_COLUMNS = ["abbreviation", "match", "pattern", "applies_to", "expansion_de", "expansion_en",
                    "category", "context", "confidence", "expand", "status", "comment"]


@dataclass
class Rule:
    index: int           # row of the library table
    abbreviation: str
    regex: re.Pattern
    is_regex: bool
    applies_to: str      # de | en | both
    expansion_de: str
    expansion_en: str
    expand: bool

    def expansion(self, language):
        """Expansion in the language of the entry; falls back to the other language."""
        first, second = (self.expansion_de, self.expansion_en) if language == "de" else (self.expansion_en, self.expansion_de)
        return first or second


def _pattern(abbr, match, pattern):
    """Regular expression of one library row."""
    if match == "regex":
        return re.compile(pattern)
    trailing_dot = abbr.endswith(".")
    base = abbr.rstrip(".")
    # internal full stops: "i.O.", "n.i.O." (an optional space is tolerated after each one)
    body = r"\.\s?".join(re.escape(part) for part in base.split("."))
    after = rf"(?![{LETTERS}0-9])"
    if match == "exact_dot":
        tail = r"\."
    elif trailing_dot:
        tail = rf"(?:\.|{after})"      # "ca." and "ca"
    else:
        # "50 Stk. in Klärung": the full stop belongs to the abbreviation when the next word starts in
        # lower case or with a digit (it cannot start a sentence); "... 50 Stk. Lieferung" keeps it
        tail = rf"{after}(?-i:\.(?=\s+[a-zäöüß0-9(]))?"   # (?-i: even for ignore_case rows
    flags = re.IGNORECASE if match == "ignore_case" else 0
    return re.compile(rf"(?<![{LETTERS}]){body}{tail}", flags)


class Library:
    def __init__(self, table):
        self.table = table
        rules = []
        for index, row in enumerate(table.itertuples(index=False)):
            rules.append(Rule(
                index=index, abbreviation=row.abbreviation, regex=_pattern(row.abbreviation, row.match, row.pattern),
                is_regex=row.match == "regex", applies_to=row.applies_to,
                expansion_de=row.expansion_de, expansion_en=row.expansion_en,
                expand=str(row.expand).strip().lower() == "yes"))
        # regular expressions first, then the longest abbreviations ("n.i.O." before "i.O.")
        self.rules = sorted(rules, key=lambda r: (not r.is_regex, -len(r.abbreviation)))


def load_library(path=LIBRARY_PATH):
    table = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED_COLUMNS if c not in table.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    return Library(table)


def validate(path=LIBRARY_PATH):
    """List of problems found in the library (empty list = valid)."""
    problems = []
    table = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    for i, row in table.iterrows():
        line = i + 2
        if row["match"] not in MATCH_TYPES:
            problems.append(f"line {line}: unknown match type '{row['match']}'")
        if row["applies_to"] not in {"de", "en", "both"}:
            problems.append(f"line {line}: applies_to must be de, en or both")
        if row["expand"] not in {"yes", "no"}:
            problems.append(f"line {line}: expand must be yes or no")
        if row["expand"] == "yes" and not (row["expansion_de"] or row["expansion_en"]):
            problems.append(f"line {line}: '{row['abbreviation']}' is set to expand but has no expansion")
        if row["expand"] == "yes" and row["confidence"] != "high":
            problems.append(f"line {line}: '{row['abbreviation']}' is set to expand but its confidence is not high "
                            "(only certain meanings are written out)")
        if row["match"] == "regex":
            try:
                re.compile(row["pattern"])
            except re.error as exc:
                problems.append(f"line {line}: invalid pattern ({exc})")
    dup = table[table.duplicated(["abbreviation", "match"], keep=False)]
    problems += [f"duplicate row: {a} ({m})" for a, m in zip(dup["abbreviation"], dup["match"])]
    return problems


def _starts_sentence(text, position):
    before = text[:position].rstrip()
    return not before or before[-1] in ".!?:"


def expand_text(text, language, library):
    """Write out the abbreviations of ONE entry. Only rows with expand = yes and valid for `language`."""
    for rule in library.rules:
        if not rule.expand or rule.applies_to not in ("both", language):
            continue

        def substitute(match, rule=rule):
            replacement = match.expand(rule.expansion(language)) if rule.is_regex else rule.expansion(language)
            if not replacement:
                return match.group(0)
            if _starts_sentence(match.string, match.start()):
                replacement = replacement[0].upper() + replacement[1:]
            following = match.string[match.end():match.end() + 1]
            if match.group(0).endswith(".") and following.isalnum():
                replacement += " "          # "Purch.Group" -> "Purchasing Group"
            return replacement

        text = rule.regex.sub(substitute, text)
    return text


def expand_comment(comment, languages, library):
    """Comment = entries separated by a line break; `languages` = one 'de'/'en' per entry."""
    entries = split_cell(comment)
    if len(languages) != len(entries):
        languages = (list(languages) + ["en"] * len(entries))[:len(entries)]
    return join_entries(expand_text(e, lang, library) for e, lang in zip(entries, languages))


# --------------------------------------------------------------------------------------
# Review sheet for the planners and discovery of abbreviations not yet in the library
# --------------------------------------------------------------------------------------
def _entries(df):
    """(entry text, language) pairs of every comment of cleaned_comments.csv."""
    pairs = set()
    for comment, languages in zip(df["Comment"], df["Entry_Languages"]):
        for entry, lang in zip(split_cell(comment), str(languages).split("|")):
            pairs.add((entry, lang))
    return sorted(pairs)


def build_review(library, df):
    """One row per library row: how often it occurs, an example, and the expansion that would result."""
    pairs = _entries(df)
    by_index = {r.index: r for r in library.rules}
    rows = []
    for index, row in enumerate(library.table.itertuples(index=False)):
        rule = by_index[index]
        hits = [(e, lang) for e, lang in pairs if rule.regex.search(e)]
        example = ""
        if hits:
            entry, lang = min(hits, key=lambda h: len(h[0]))
            example = entry[:140]
        rows.append({**row._asdict(), "entries_with_abbreviation": len(hits), "example": example})
    out = pd.DataFrame(rows)
    if os.path.exists(EVIDENCE_PATH):
        evidence = pd.read_csv(EVIDENCE_PATH, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        out = out.merge(evidence, on=["abbreviation", "match"], how="left").rename(columns={"evidence_note": "evidence"})
    order = ["confidence", "entries_with_abbreviation"]
    out["_c"] = out["confidence"].map({"low": 0, "medium": 1, "high": 2})
    return out.sort_values(["_c", "entries_with_abbreviation"], ascending=[True, False]).drop(columns="_c")


def build_sheet(library, df):
    """Simple table for the planners: abbreviation, meaning, language of the entries where it was found
    (DE / EN, from the language detection of the pipeline). One row per abbreviation and language; the
    meaning is the proposed expansion in that language (empty when nothing is proposed yet)."""
    pairs = _entries(df)
    rows = []
    for rule, row in zip(library.rules, library.table.itertuples(index=False)):
        found = {lang for entry, lang in pairs if rule.regex.search(entry)}
        for lang in sorted(found):
            first, second = (row.expansion_de, row.expansion_en) if lang == "de" else (row.expansion_en, row.expansion_de)
            rows.append({"Abbreviation": row.abbreviation, "Meaning": first or second, "Language": lang.upper()})
    out = pd.DataFrame(rows, columns=["Abbreviation", "Meaning", "Language"])
    return out.sort_values(["Abbreviation", "Language"], key=lambda c: c.str.lower()).reset_index(drop=True)


def write_sheet(sheet, path=SHEET_PATH):
    """Excel file with minimal layout: bold header, column widths, nothing else."""
    from openpyxl.styles import Font
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sheet.to_excel(writer, index=False, sheet_name="Abbreviations")
        ws = writer.sheets["Abbreviations"]
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for column, width in zip("ABC", (18, 60, 10)):
            ws.column_dimensions[column].width = width
        ws.freeze_panes = "A2"


def discover(library, df, min_count=2):
    """Abbreviation-like words that no library row matches yet: words with a full stop inside, a word of
    at most 6 letters followed by a full stop and a lower-case word or number ("Wtl. Bedarf"), and words of
    2 to 6 capitals. The text matched by the library is masked first."""
    import collections
    counter = collections.Counter()
    for entry, _ in _entries(df):
        for rule in library.rules:
            entry = rule.regex.sub(" ", entry)
        found = set(re.findall(rf"(?<![{LETTERS}])(?:[{LETTERS}]\.){{2,}}", entry))                       # z.B., i.O.
        found |= set(re.findall(rf"(?<![{LETTERS}])[{LETTERS}]{{2,6}}\.(?=\s+[a-zäöüß0-9])", entry))    # Wtl. Bedarf
        found |= {t for t in re.findall(rf"(?<![{LETTERS}0-9])[{LETTERS}]{{2,6}}(?![{LETTERS}0-9])", entry) if t.isupper()}
        counter.update(found)
    return [(t, n) for t, n in counter.most_common() if n >= min_count]


if __name__ == "__main__":
    library = load_library()
    if "--check" in sys.argv or len(sys.argv) == 1:
        problems = validate()
        table = library.table
        print(f"{len(table)} rows | expand=yes: {(table['expand'] == 'yes').sum()} | to confirm: {(table['expand'] == 'no').sum()}")
        print("\n".join(problems) if problems else "Library valid.")
    if "--report" in sys.argv or "--discover" in sys.argv or "--sheet" in sys.argv:
        path = sys.argv[sys.argv.index("--comments") + 1] if "--comments" in sys.argv else COMMENTS_PATH
        df = pd.read_csv(path, usecols=["Comment", "Entry_Languages"])
    if "--report" in sys.argv:
        review = build_review(library, df)
        review.to_csv(REVIEW_PATH, index=False, encoding="utf-8-sig")
        print(f"Review sheet written: {REVIEW_PATH} (confidential: contains excerpts of comments)")
    if "--sheet" in sys.argv:
        sheet = build_sheet(library, df)
        write_sheet(sheet)
        print(f"Excel sheet written: {SHEET_PATH} ({len(sheet)} rows)")
    if "--discover" in sys.argv:
        print("Not in the library yet (word, number of entries):")
        for token, n in discover(library, df):
            print(f"  {token}: {n}")

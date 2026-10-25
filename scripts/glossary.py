"""
DeepL glossary for the German supply-chain jargon that DeepL translates inconsistently or wrongly
(e.g. "Vorzug" -> priority / preference, "Abriss" -> demolition, "Rückbuchung" -> refund).

* Source of truth: lexicon/glossary_de_en.csv (versioned, generic notes only, no real comment excerpts).
  Only rows with use = yes AND confidence = high are sent to DeepL, the others are proposals that the
  planners validate (columns status, reviewer, reviewer_comment), same rule as the abbreviation library.
* DeepL matches glossary terms case-sensitively and, in practice, on the exact written form: inflected
  forms (plural, participle) are therefore listed as separate rows.
* The glossary is created once on DeepL and reused: its id and a content hash are kept in
  data/interim/deepl_glossary.json. When the CSV changes, the old glossary is deleted and a new one created.
* The glossary only contains generic vocabulary: nothing confidential is uploaded.

Usage:  python scripts/glossary.py --check     (validates the CSV and lists the active terms)
"""

import hashlib
import json
import os
import re
import sys

import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
GLOSSARY_PATH = os.path.join(project_dir, "lexicon", "glossary_de_en.csv")
STATE_PATH = os.path.join(project_dir, "data", "interim", "deepl_glossary.json")

COLUMNS = ["term_de", "translation_en", "category", "context", "confidence", "use", "status",
           "comment", "reviewer", "reviewer_comment"]
LETTER = "A-Za-zÄÖÜäöüß0-9"


def read_glossary(path=GLOSSARY_PATH):
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def validate(df):
    """List of problems found in the glossary table (empty list = valid)."""
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        return [f"missing columns: {missing}"]
    problems = []
    for i, row in df.iterrows():
        line = i + 2
        for column in ("term_de", "translation_en"):
            value = row[column]
            if not value.strip():
                problems.append(f"line {line}: {column} is empty")
            elif value != value.strip() or any(ch in value for ch in "\t\n\r"):
                problems.append(f"line {line}: {column} has spaces around it, a tab or a line break")
        if row["confidence"] not in ("high", "medium", "low"):
            problems.append(f"line {line}: confidence must be high / medium / low")
        if row["use"] not in ("yes", "no"):
            problems.append(f"line {line}: use must be yes / no")
        if row["use"] == "yes" and row["confidence"] != "high":
            problems.append(f"line {line}: use = yes requires confidence = high")
    for term in df["term_de"][df["term_de"].duplicated()]:
        problems.append(f"duplicated term: {term}")
    return problems


def load_entries(path=GLOSSARY_PATH):
    """{German term: English term} for the rows sent to DeepL (use = yes and confidence = high)."""
    if not os.path.exists(path):
        return {}
    df = read_glossary(path)
    problems = validate(df)
    if problems:
        raise ValueError("Invalid glossary " + path + ": " + "; ".join(problems))
    active = df[(df["use"] == "yes") & (df["confidence"] == "high")]
    return dict(zip(active["term_de"], active["translation_en"]))


def entries_hash(entries):
    """Short fingerprint of the active entries (changes whenever a term or a translation changes)."""
    payload = json.dumps(sorted(entries.items()), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def term_pattern(entries):
    """Regex finding any active German term as a whole word (case-sensitive, like DeepL)."""
    if not entries:
        return None
    terms = sorted(entries, key=len, reverse=True)
    return re.compile(rf"(?<![{LETTER}])(?:{'|'.join(map(re.escape, terms))})(?![{LETTER}])")


def contains_term(text, pattern):
    return bool(pattern and pattern.search(text))


def _read_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ensure_glossary(translator, entries, state_path=None):
    """Id of the DeepL glossary matching `entries`: reused if the content is unchanged and it still
    exists on DeepL, otherwise (re)created. Returns None when there is nothing to send."""
    if not entries:
        return None
    state_path = state_path or STATE_PATH
    digest = entries_hash(entries)
    state = _read_state(state_path)
    if state.get("id"):
        if state.get("hash") == digest:
            try:
                translator.get_glossary(state["id"])
                return state["id"]
            except Exception:   # deleted on the DeepL side: create it again below
                pass
        try:
            translator.delete_glossary(state["id"])   # outdated version: do not accumulate glossaries
        except Exception:
            pass
    info = translator.create_glossary(f"roche-poc-de-en-{digest}", "DE", "EN", dict(entries))
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"hash": digest, "id": info.glossary_id}, f)
    return info.glossary_id


if __name__ == "__main__":
    df = read_glossary()
    problems = validate(df)
    if problems:
        print("❌ Glossary invalid:\n  " + "\n  ".join(problems))
        sys.exit(1)
    entries = load_entries()
    print(f"✅ {len(df)} rows | {len(entries)} sent to DeepL (use = yes, confidence = high) | "
          f"{len(df) - len(entries)} proposals to validate | hash {entries_hash(entries)}")
    for term, english in entries.items():
        print(f"  {term:20} -> {english}")

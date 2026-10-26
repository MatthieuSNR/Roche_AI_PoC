"""
Translation: adds comment_language and Comment_EN to data/cleaned_comments.csv.

* Entry by entry: a comment cell is a journal of several entries, one per line (see data_cleaning.py).
  Each entry has its own language and is translated, cached and pseudonymised on its own; the
  translated entries are put back one per line in Comment_EN. The text translated is Comment_Expanded
  (abbreviations written out, scripts/abbreviations.py) when that column exists.
* Language: the comments are English or German only. langdetect alone labels short,
  jargon-heavy comments as Hungarian, Catalan, Norwegian... and those were never
  translated, so detection is restricted to 'en' / 'de' (+ a small German lexicon).
* Translation: DeepL, German comments only. Every translation is stored in
  data/interim/translation_cache.csv, so a text is paid for once, even if the script
  is interrupted or re-run after a new data build.
* Pseudonymisation: before a text is sent to DeepL, e-mail addresses, supplier names,
  material numbers, long numbers (PO, batch) and the company name are replaced by
  placeholders (scripts/pseudonymise.py). The originals are put back locally after
  translation, so they never leave this machine.

* Glossary: lexicon/glossary_de_en.csv (scripts/glossary.py) fixes the German jargon DeepL gets wrong
  ("Vorzug" -> pull-in, "Abriss" -> supply gap...). Only validated terms (use = yes, confidence = high)
  are uploaded. The cache remembers which glossary version each translation used; translations made
  before, or with an older glossary, that contain a glossary term are redone only with --refresh-glossary.

Usage (from the project root):  python scripts/translation.py            (translates)
                                python scripts/translation.py --dry-run  (counts only)
                                python scripts/translation.py --refresh-glossary   (also redo the stale ones)
                                python scripts/translation.py --no-glossary        (ignore the glossary)
"""

import os
import re
import sys
import time

import pandas as pd
from langdetect import DetectorFactory, detect_langs

import glossary as glossary_module
from entries import join_entries, split_cell
from pseudonymise import build_patterns, person_names, pseudonymise, report, restore, vendor_names

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMENTS_PATH = os.path.join(project_dir, "data", "cleaned_comments.csv")
CACHE_PATH = os.path.join(project_dir, "data", "interim", "translation_cache.csv")
# Earlier versions of cleaned_comments.csv: their Comment_EN translations were merged into the cache, which
# now holds all of them (checked 26.10: 960 of 960). They are no longer read, so that a translation removed
# from the cache to be redone (e.g. a wrong "Vorzug") does not come back from there.
OLD_TRANSLATED_FILES = []


DetectorFactory.seed = 0  # make langdetect reproducible

GERMAN_HINTS = re.compile(
    r"[äöüß]|\b(und|nicht|der|die|das|dem|den|des|wird|werden|bei|mit|für|von|vom|auf|ist|sind|"
    r"noch|aber|wegen|nach|zum|zur|kein\w*|liefer\w*|bestell\w*|verschieb\w*|klärung|woche\w*|"
    r"stück|stk|fehlt\w*|ware|bitte|offen|termin\w*|vorzug\w*|beschleunig\w*|lager\w*|korrektur\w*|"
    r"am|im|zu|ein\w*|bis|aus)\b",
    re.IGNORECASE,
)


def detect_language(text):
    """Return 'en', 'de' or 'unknown' (empty text only)."""
    if pd.isna(text) or not str(text).strip():
        return "unknown"
    text = str(text)
    try:
        scores = {c.lang: c.prob for c in detect_langs(text)}
    except Exception:  # digits only, very short text
        scores = {}
    en, de = scores.get("en", 0.0), scores.get("de", 0.0)
    if en or de:
        return "de" if de > en else "en"
    return "de" if GERMAN_HINTS.search(text) else "en"


def normalize(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def load_cache():
    """Cache = every translation already paid for (the cache file; + old Comment_EN columns if listed)."""
    cache = {}
    if os.path.exists(CACHE_PATH):
        c = pd.read_csv(CACHE_PATH, dtype=str, keep_default_na=False)
        cache.update(zip(c["source_text"], c["translation"]))
    for path in OLD_TRANSLATED_FILES:
        if os.path.exists(path):
            old = pd.read_csv(path, usecols=["Comment", "Comment_EN"]).dropna()
            old = old[old["Comment"] != old["Comment_EN"]]
            for source, english in zip(old["Comment"], old["Comment_EN"]):
                cache.setdefault(normalize(source), str(english))
    return cache


def load_marks():
    """{source text: hash of the glossary used for its translation} (absent = translated without glossary)."""
    if os.path.exists(CACHE_PATH):
        c = pd.read_csv(CACHE_PATH, dtype=str, keep_default_na=False)
        if "glossary" in c.columns:
            return {s: g for s, g in zip(c["source_text"], c["glossary"]) if g}
    return {}


def save_cache(cache, marks=None):
    """Writes the cache; `marks` (glossary hash per text) is kept from the file when not given."""
    marks = load_marks() if marks is None else marks
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    pd.DataFrame({"source_text": list(cache), "translation": list(cache.values()),
                  "glossary": [marks.get(t, "") for t in cache]}).to_csv(CACHE_PATH, index=False)


def stale_entries(texts, cache, marks, entries):
    """Cached texts containing a glossary term but translated without the current glossary version."""
    pattern = glossary_module.term_pattern(entries)
    digest = glossary_module.entries_hash(entries) if entries else None
    return [t for t in texts if t in cache and glossary_module.contains_term(t, pattern) and marks.get(t) != digest]


def protect_terms(text, patterns, forced):
    """pseudonymise() + the forced glossary terms written in English inside <keep> tags (copied unchanged by
    DeepL): returns (text to send, mapping placeholder -> value to put back)."""
    if not forced:
        return pseudonymise(text, patterns)
    safe, mapping = pseudonymise(text, list(patterns) + [("TERM", glossary_module.forced_pattern(forced))])
    return safe, {k: forced.get(v, v) if k.startswith("TERM_") else v for k, v in mapping.items()}


def sentence_case(text, terms):
    """A forced term is copied as written ("pull-in"): capital letter at the start of a sentence."""
    for term in {t for t in terms if t[:1].islower()}:
        text = re.sub(rf"(^|[.!?:]\s+|\n|-\s|--> ?)({re.escape(term)})", lambda m: m.group(1) + m.group(2)[0].upper() + m.group(2)[1:], text)
    return text


def translate_missing(texts, cache, patterns, batch_size=50, glossary_entries=None, marks=None, translator=None,
                      forced=None):
    """Translate with DeepL the texts not in the cache; checkpoint after every batch.
    Only the pseudonymised version of each text is sent; the cache keeps the original.
    With glossary_entries, the DeepL glossary is created/reused and applied; if it cannot be set up,
    the translation continues without it (and the texts are not marked, so --refresh-glossary can redo them)."""
    try:
        import deepl
        rate_limit = deepl.TooManyRequestsException
    except ImportError:    # only with an injected translator (tests)
        rate_limit = ()
    marks = {} if marks is None else marks
    if translator is None:
        from config import DEEPL_API_KEY
        translator = deepl.Translator(DEEPL_API_KEY)

    glossary_id, digest = None, None
    if glossary_entries:
        try:
            glossary_id = glossary_module.ensure_glossary(translator, glossary_entries)
            digest = glossary_module.entries_hash(glossary_entries)
            print(f"DeepL glossary in use: {len(glossary_entries)} terms ({digest})")
        except Exception as exc:
            print(f"⚠️ DeepL glossary unavailable ({exc}); translating without it.")
    options = {"glossary": glossary_id} if glossary_id else {}

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        safe = [protect_terms(t, patterns, forced) for t in batch]  # [(text with placeholders, mapping)]
        for attempt in range(3):
            try:
                results = translator.translate_text(
                    [t for t, _ in safe], source_lang="DE", target_lang="EN-US",
                    tag_handling="xml", ignore_tags=["keep"], **options,
                )
                break
            except rate_limit:
                print("Rate limit reached, waiting...")
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError("DeepL rate limit: try again later (progress is saved).")
        cache.update(zip(batch, [sentence_case(restore(r.text, m), (forced or {}).values())
                                 for r, (_, m) in zip(results, safe)]))
        if glossary_id:
            marks.update({t: digest for t in batch})
        else:
            for t in batch:
                marks.pop(t, None)
        save_cache(cache, marks)
        print(f"  translated {min(start + batch_size, len(texts))}/{len(texts)}")
    usage = translator.get_usage().character
    print(f"DeepL characters used this month: {usage.count} / {usage.limit}")


def entry_languages(df, text_column):
    """Language ('de' / 'en') of every entry of every comment: read from Entry_Languages (written by
    data_cleaning.py, detected on the original wording) or, if missing, detected here."""
    known = df["Entry_Languages"] if "Entry_Languages" in df.columns else [None] * len(df)
    result = []
    for text, langs in zip(df[text_column], known):
        entries = split_cell(text)
        if isinstance(langs, str) and len(langs.split("|")) == len(entries):
            result.append(langs.split("|"))
        else:
            result.append([detect_language(e) for e in entries])
    return result


def add_translations(df, dry_run=False, refresh_glossary=False, use_glossary=True, translator=None):
    df = df.copy()
    text_column = "Comment_Expanded" if "Comment_Expanded" in df.columns else "Comment"
    languages = entry_languages(df, text_column)
    df["Entry_Languages"] = ["|".join(langs) for langs in languages]
    df["comment_language"] = ["de" if "de" in langs else "en" for langs in languages]
    cache = load_cache()

    entries = [[normalize(e) for e in split_cell(t)] for t in df[text_column]]
    texts = sorted({e for row, langs in zip(entries, languages) for e, lang in zip(row, langs) if lang == "de" and e})
    todo = [t for t in texts if t not in cache]
    print(f"German entries: {len(texts)} distinct texts | already translated: {len(texts) - len(todo)} "
          f"| to translate: {len(todo)} ({sum(map(len, todo))} characters)")

    glossary_entries = glossary_module.load_entries() if use_glossary else {}
    marks = load_marks()
    stale = stale_entries(texts, cache, marks, glossary_entries)
    if glossary_entries:
        print(f"Glossary: {len(glossary_entries)} active terms | cached translations made without the current "
              f"glossary version that contain a term: {len(stale)} ({sum(map(len, stale))} characters)"
              + ("" if refresh_glossary or not stale else "  -> --refresh-glossary to redo them"))
    if refresh_glossary and stale:
        todo = todo + stale

    persons = person_names(df["SOURCING_MANAGER"]) if "SOURCING_MANAGER" in df.columns else []
    patterns = build_patterns(vendor_names(df["VENDOR_NAME"]), df["MATERIAL_NUMBER"].dropna().astype(str).tolist(), persons)
    if todo:
        counts = report(todo, patterns)
        print("Pseudonymised before sending (number of texts):", counts.to_dict() if len(counts) else "nothing")
    if todo and not dry_run:
        forced = glossary_module.forced_entries() if use_glossary else {}
        translate_missing(todo, cache, patterns, glossary_entries=glossary_entries, marks=marks, translator=translator,
                          forced=forced)
    save_cache(cache, marks)
    return apply_cache(df, cache)[0]


def apply_cache(df, cache=None):
    """comment_language and Comment_EN from the translation cache only: no DeepL call, no cost.
    Used by add_translations and when data_cleaning saves the file, so that a rebuild keeps the
    translations already paid for. A German entry not yet in the cache stays in German in Comment_EN.
    Returns (table, missing): missing = the distinct German entries not in the cache."""
    df = df.copy()
    text_column = "Comment_Expanded" if "Comment_Expanded" in df.columns else "Comment"
    languages = entry_languages(df, text_column)
    df["Entry_Languages"] = ["|".join(langs) for langs in languages]
    df["comment_language"] = ["de" if "de" in langs else "en" for langs in languages]
    cache = load_cache() if cache is None else cache

    entries = [[normalize(e) for e in split_cell(t)] for t in df[text_column]]
    df["Comment_EN"] = [join_entries(cache.get(e, e) if lang == "de" else e for e, lang in zip(row, langs))
                        for row, langs in zip(entries, languages)]
    missing = sorted({e for row, langs in zip(entries, languages) for e, lang in zip(row, langs)
                      if lang == "de" and e and e not in cache})
    return df, missing


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # for config.py
    dry_run = "--dry-run" in sys.argv
    df = pd.read_csv(COMMENTS_PATH)
    df = add_translations(df, dry_run=dry_run, refresh_glossary="--refresh-glossary" in sys.argv,
                          use_glossary="--no-glossary" not in sys.argv)
    print(df["comment_language"].value_counts().to_string())
    if not dry_run:
        df.to_csv(COMMENTS_PATH, index=False)
        print(f"✅ Comment_EN added to {COMMENTS_PATH}")

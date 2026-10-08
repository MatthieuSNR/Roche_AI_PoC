"""
Translation: adds comment_language and Comment_EN to data/cleaned_comments.csv.

* Language: the comments are English or German only. langdetect alone labels short,
  jargon-heavy comments as Hungarian, Catalan, Norwegian... and those were never
  translated, so detection is restricted to 'en' / 'de' (+ a small German lexicon).
* Translation: DeepL, German comments only. Every translation is stored in
  data/interim/translation_cache.csv, so a text is paid for once, even if the script
  is interrupted or re-run after a new data build.

Usage (from the project root):  python scripts/translation.py            (translates)
                                python scripts/translation.py --dry-run  (counts only)
"""

import os
import re
import sys
import time

import pandas as pd
from langdetect import DetectorFactory, detect_langs

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMENTS_PATH = os.path.join(project_dir, "data", "cleaned_comments.csv")
CACHE_PATH = os.path.join(project_dir, "data", "interim", "translation_cache.csv")
# Earlier versions of cleaned_comments.csv: their Comment_EN translations are reused
OLD_TRANSLATED_FILES = [os.path.join(project_dir, "data", "interim", "cleaned_comments_before_rebuild.csv")]

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
    """Cache = every translation already paid for: the cache file + old Comment_EN columns."""
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


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    pd.DataFrame({"source_text": list(cache), "translation": list(cache.values())}).to_csv(CACHE_PATH, index=False)


def translate_missing(texts, cache, batch_size=50):
    """Translate with DeepL the texts not in the cache; checkpoint after every batch."""
    import deepl
    from config import DEEPL_API_KEY

    translator = deepl.Translator(DEEPL_API_KEY)
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        for attempt in range(3):
            try:
                results = translator.translate_text(batch, source_lang="DE", target_lang="EN-US")
                break
            except deepl.TooManyRequestsException:
                print("Rate limit reached, waiting...")
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError("DeepL rate limit: try again later (progress is saved).")
        cache.update(zip(batch, [r.text for r in results]))
        save_cache(cache)
        print(f"  translated {min(start + batch_size, len(texts))}/{len(texts)}")
    usage = translator.get_usage().character
    print(f"DeepL characters used this month: {usage.count} / {usage.limit}")


def add_translations(df, dry_run=False):
    df = df.copy()
    df["comment_language"] = df["Comment"].map(detect_language)
    cache = load_cache()

    german = df["comment_language"] == "de"
    texts = df.loc[german, "Comment"].map(normalize).unique().tolist()
    todo = [t for t in texts if t not in cache]
    print(f"German comments: {len(texts)} distinct texts | already translated: {len(texts) - len(todo)} "
          f"| to translate: {len(todo)} ({sum(map(len, todo))} characters)")

    if todo and not dry_run:
        translate_missing(todo, cache)
    save_cache(cache)

    df["Comment_EN"] = df["Comment"]
    df.loc[german, "Comment_EN"] = df.loc[german, "Comment"].map(normalize).map(cache).fillna(df.loc[german, "Comment"])
    return df


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # for config.py
    dry_run = "--dry-run" in sys.argv
    df = pd.read_csv(COMMENTS_PATH)
    df = add_translations(df, dry_run=dry_run)
    print(df["comment_language"].value_counts().to_string())
    if not dry_run:
        df.to_csv(COMMENTS_PATH, index=False)
        print(f"✅ Comment_EN added to {COMMENTS_PATH}")

"""Tokenisation and lemmatisation (spaCy). Models are loaded lazily and once."""

from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from roche_poc import config

_MODELS = {"en": "en_core_web_sm", "de": "de_core_news_sm"}


@lru_cache(maxsize=None)
def _nlp(lang: str):
    import spacy

    return spacy.load(_MODELS.get(lang, _MODELS["en"]), disable=["parser", "ner"])


def basic_clean(text: str) -> str:
    """Lower-case, remove punctuation, collapse whitespace."""
    text = re.sub(r"[^\w\s]", " ", str(text).lower())
    return re.sub(r"\s+", " ", text).strip()


def lemmatize(text, lang: str = "en") -> list[str]:
    """Lemmas without stop-words, numbers or single characters."""
    if pd.isna(text):
        return []
    doc = _nlp(lang)(basic_clean(text))
    return [t.lemma_ for t in doc if not t.is_stop and not t.is_digit and len(t.lemma_) > 1]


def add_tokens(comments: pd.DataFrame, text_col: str = config.COL_COMMENT_EN) -> pd.DataFrame:
    """Lemmatise the English text (translated), so a single spaCy model is enough."""
    out = comments.copy()
    out["tokens"] = out[text_col].map(lambda t: lemmatize(t, "en"))
    return out

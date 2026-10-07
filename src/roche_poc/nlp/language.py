"""Language detection for planner comments (mostly English or German)."""

from __future__ import annotations

import pandas as pd

from roche_poc import config

_seeded = False


def detect_language(text) -> str:
    """Return ``'en'``, ``'de'``, another ISO code, or ``'unknown'`` (empty / undecidable).

    langdetect is non-deterministic unless seeded; the seed is fixed on first use.
    """
    global _seeded
    from langdetect import DetectorFactory, detect

    if not _seeded:
        DetectorFactory.seed = 0
        _seeded = True
    if pd.isna(text) or not str(text).strip():
        return "unknown"
    try:
        return detect(str(text))
    except Exception:  # very short or ambiguous text
        return "unknown"


def add_language_column(comments: pd.DataFrame, text_col: str = config.COL_COMMENT) -> pd.DataFrame:
    out = comments.copy()
    out[config.COL_LANGUAGE] = out[text_col].map(detect_language)
    return out

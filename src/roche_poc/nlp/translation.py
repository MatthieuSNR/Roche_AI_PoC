"""German -> English translation with DeepL.

Quota safety (free plan: 500 000 characters / month):
* only comments detected as German are sent;
* each distinct text is translated once (the ``comments`` table is already unique);
* every batch is written to a cache file, so an interruption never costs quota twice.

Data governance: DeepL is a cloud service, unlike the local LLM. The text sent is the
planner comment only (no vendor or material identifier), but this remains a limit to
discuss in the thesis; see ``docs/architecture.md``.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from roche_poc import config
from roche_poc.nlp.language import add_language_column

log = logging.getLogger(__name__)
_CACHE_COLUMNS = ["source_text", "translation"]


def _load_cache(path: Path | None) -> dict[str, str]:
    if path is None or not Path(path).exists():
        return {}
    cache = pd.read_parquet(path)
    return dict(zip(cache["source_text"], cache["translation"]))


def _save_cache(cache: dict[str, str], path: Path | None) -> None:
    if path is None:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"source_text": list(cache), "translation": list(cache.values())}).to_parquet(
        path, index=False
    )


def _make_translator():
    import deepl

    return deepl.Translator(config.get_deepl_key())


def _translate_batch(translator, batch: list[str], retries: int = 3) -> list[str]:
    for attempt in range(retries):
        try:
            return [r.text for r in translator.translate_text(batch, target_lang="EN-US")]
        except Exception as exc:  # deepl.TooManyRequestsException without importing deepl
            if "TooManyRequests" in type(exc).__name__ and attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def enrich_comments(
    comments: pd.DataFrame,
    translator=None,
    cache_path: Path | None = config.TRANSLATION_CACHE_PATH,
    batch_size: int = 50,
) -> pd.DataFrame:
    """Add ``comment_language`` and ``Comment_EN`` (translation if German, original otherwise)."""
    out = add_language_column(comments)
    out[config.COL_COMMENT_EN] = out[config.COL_COMMENT]

    german = out[config.COL_LANGUAGE] == "de"
    texts = out.loc[german, config.COL_COMMENT].astype(str).unique().tolist()
    cache = _load_cache(cache_path)
    todo = [t for t in texts if t not in cache]
    log.info("%d German texts, %d already cached, %d to translate (%d chars)",
             len(texts), len(texts) - len(todo), len(todo), sum(map(len, todo)))

    if todo:
        translator = translator or _make_translator()
        for start in range(0, len(todo), batch_size):
            batch = todo[start : start + batch_size]
            cache.update(zip(batch, _translate_batch(translator, batch)))
            _save_cache(cache, cache_path)  # real checkpoint after every batch

    out.loc[german, config.COL_COMMENT_EN] = (
        out.loc[german, config.COL_COMMENT].astype(str).map(cache).fillna(out.loc[german, config.COL_COMMENT])
    )
    return out

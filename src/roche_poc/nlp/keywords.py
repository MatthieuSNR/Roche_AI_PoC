"""Keywords per root cause (TF-IDF over one document per root cause).

Why TF-IDF and not raw counts: raw frequencies are dominated by words common to all
causes ("supplier", "delivery"); inverse document frequency keeps the words that
*distinguish* one root cause from the others. Input is the English text.
"""

from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from roche_poc import config

_TOKEN_PATTERN = r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b"  # words only (drops numbers, codes)


def top_keywords_by_root_cause(
    comments: pd.DataFrame,
    n: int = 8,
    text_col: str = config.COL_COMMENT_EN,
    min_comments: int = 5,
) -> dict[str, list[tuple[str, float]]]:
    """Return ``{root_cause: [(keyword, tfidf_score), ...]}`` for causes with enough comments."""
    known = comments.dropna(subset=[config.COL_ROOT_CAUSE, text_col])
    sizes = known[config.COL_ROOT_CAUSE].value_counts()
    causes = sizes[sizes >= min_comments].index.tolist()
    if len(causes) < 2:
        return {}
    docs = [" ".join(known.loc[known[config.COL_ROOT_CAUSE] == c, text_col].astype(str)) for c in causes]
    vectorizer = TfidfVectorizer(stop_words="english", token_pattern=_TOKEN_PATTERN, sublinear_tf=True)
    matrix = vectorizer.fit_transform(docs)
    vocab = vectorizer.get_feature_names_out()
    result = {}
    for i, cause in enumerate(causes):
        row = matrix.getrow(i).toarray().ravel()
        best = row.argsort()[::-1][:n]
        result[cause] = [(str(vocab[j]), round(float(row[j]), 3)) for j in best if row[j] > 0]
    return result

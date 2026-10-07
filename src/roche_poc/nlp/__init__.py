"""Classical NLP: deterministic, reproducible text processing.

language       language detection (langdetect, seeded)
translation    DE -> EN with DeepL, cached and checkpointed (quota-safe)
preprocessing  tokenisation and lemmatisation (spaCy en/de)
keywords       TF-IDF keywords per root cause
themes         (empty) embeddings + clustering of sub-themes inside a root cause

What belongs here rather than in ``llm``: anything that must give the same result on
the same input and be measurable (counting, extraction, clustering).
"""

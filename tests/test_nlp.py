import pandas as pd

from roche_poc import config
from roche_poc.nlp import keywords, translation


class FakeTranslator:
    calls = 0

    def translate_text(self, batch, target_lang):
        FakeTranslator.calls += 1
        return [type("R", (), {"text": "EN:" + t})() for t in batch]


def test_enrich_translates_only_german_and_skips_cache(monkeypatch=None):
    # language detection needs langdetect: inject the language column instead.
    from roche_poc.nlp import language

    comments = pd.DataFrame({config.COL_COMMENT: ["Lieferverzögerung beim Lieferanten", "Waiting for material"]})
    orig = language.detect_language
    language.detect_language = lambda t: "de" if "Lieferant" in str(t) else "en"
    try:
        out = translation.enrich_comments(comments, translator=FakeTranslator(), cache_path=None)
    finally:
        language.detect_language = orig
    assert out[config.COL_COMMENT_EN].tolist() == ["EN:Lieferverzögerung beim Lieferanten", "Waiting for material"]
    assert FakeTranslator.calls == 1


def test_keywords_separate_root_causes():
    rows = (
        [{config.COL_ROOT_CAUSE: "Material", config.COL_COMMENT_EN: "waiting raw material shortage"}] * 6
        + [{config.COL_ROOT_CAUSE: "Machine", config.COL_COMMENT_EN: "machine breakdown capacity strike"}] * 6
    )
    result = keywords.top_keywords_by_root_cause(pd.DataFrame(rows), n=4)  # 4 equally scored words each
    assert "material" in dict(result["Material"]) and "machine" in dict(result["Machine"])
    assert "machine" not in dict(result["Material"])

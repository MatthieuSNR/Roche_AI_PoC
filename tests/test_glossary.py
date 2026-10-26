"""Tests for the DeepL jargon glossary (glossary.py + its use in translation.py).
Synthetic texts and a fake DeepL translator: no network, no API key."""
import os
import sys
import tempfile
import types

import pandas as pd

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)

import glossary as gl  # noqa: E402
import translation as tr  # noqa: E402

ENTRIES = {"Vorzug": "pull-in", "Abriss": "supply gap", "vorgezogen": "pulled in"}


class FakeTranslator:
    """Records the calls; 'translates' by prefixing the text."""
    def __init__(self, existing=()):
        self.calls, self.created, self.deleted, self.existing = [], [], [], set(existing)

    def create_glossary(self, name, source, target, entries):
        self.created.append((name, source, target, dict(entries)))
        gid = f"gid-{len(self.created)}"
        self.existing.add(gid)
        return types.SimpleNamespace(glossary_id=gid)

    def get_glossary(self, gid):
        if gid not in self.existing:
            raise KeyError(gid)

    def delete_glossary(self, gid):
        self.deleted.append(gid)
        self.existing.discard(gid)

    def translate_text(self, texts, **kw):
        self.calls.append(kw)
        return [types.SimpleNamespace(text="EN:" + t) for t in texts]

    def get_usage(self):
        return types.SimpleNamespace(character=types.SimpleNamespace(count=1, limit=2))


def _table(rows):
    return pd.DataFrame(rows, columns=gl.COLUMNS)


def _row(term="Vorzug", en="pull-in", conf="high", use="yes"):
    return [term, en, "cat", "ctx", conf, use, "proposed", "note", "", ""]


def test_real_glossary_is_valid_and_only_high_confidence_is_sent():
    df = gl.read_glossary()
    assert gl.validate(df) == []
    entries = gl.load_entries()
    assert entries and "Vorzug" in entries
    assert set(entries) == set(df[(df.use == "yes") & (df.confidence == "high")].term_de)


def test_validation_catches_mistakes():
    assert gl.validate(_table([_row(), _row()]))                      # duplicate term
    assert gl.validate(_table([_row(conf="medium", use="yes")]))      # use = yes needs high
    assert gl.validate(_table([_row(en=" pull-in")]))                 # space around the term
    assert gl.validate(_table([_row(term="")]))                       # empty term
    assert gl.validate(_table([_row(conf="sure")]))                   # unknown confidence
    assert gl.validate(pd.DataFrame({"term_de": ["a"]}))              # missing columns


def test_term_matching_is_whole_word_and_case_sensitive():
    pattern = gl.term_pattern(ENTRIES)
    assert gl.contains_term("Vorzug angefragt", pattern)
    assert gl.contains_term("wurde vorgezogen.", pattern)
    assert not gl.contains_term("Vorzugsteile", pattern)        # longer word
    assert not gl.contains_term("vorzug", pattern)              # case-sensitive
    assert not gl.contains_term("kein Treffer", pattern)


def test_hash_changes_with_content():
    assert gl.entries_hash(ENTRIES) == gl.entries_hash(dict(reversed(list(ENTRIES.items()))))
    assert gl.entries_hash(ENTRIES) != gl.entries_hash({**ENTRIES, "Abriss": "demolition"})


def test_glossary_created_once_reused_then_replaced_when_content_changes():
    state = os.path.join(tempfile.mkdtemp(), "state.json")
    t = FakeTranslator()
    first = gl.ensure_glossary(t, ENTRIES, state)
    assert gl.ensure_glossary(t, ENTRIES, state) == first and len(t.created) == 1   # reused
    assert t.created[0][1:3] == ("DE", "EN")
    second = gl.ensure_glossary(t, {**ENTRIES, "Abriss": "stock-out"}, state)       # content changed
    assert second != first and t.deleted == [first] and len(t.created) == 2
    t.existing.clear()                                                              # deleted on DeepL
    assert gl.ensure_glossary(t, {**ENTRIES, "Abriss": "stock-out"}, state) != second
    assert gl.ensure_glossary(t, {}, state) is None


def test_translation_uses_the_glossary_and_marks_the_texts(monkeypatch=None):
    tmp = tempfile.mkdtemp()
    tr.CACHE_PATH = os.path.join(tmp, "cache.csv")
    gl.STATE_PATH = os.path.join(tmp, "state.json")
    t, cache, marks = FakeTranslator(), {}, {}
    tr.translate_missing(["Vorzug angefragt"], cache, [], glossary_entries=ENTRIES, marks=marks, translator=t)
    assert t.calls[0]["glossary"] == "gid-1" and t.calls[0]["source_lang"] == "DE"
    assert cache["Vorzug angefragt"] == "EN:Vorzug angefragt"
    assert marks["Vorzug angefragt"] == gl.entries_hash(ENTRIES)
    saved = pd.read_csv(tr.CACHE_PATH, dtype=str, keep_default_na=False)
    assert saved["glossary"].tolist() == [gl.entries_hash(ENTRIES)]
    assert tr.load_marks() == {"Vorzug angefragt": gl.entries_hash(ENTRIES)}


def test_translation_falls_back_without_glossary_if_deepl_refuses_it():
    tmp = tempfile.mkdtemp()
    tr.CACHE_PATH = os.path.join(tmp, "cache.csv")
    gl.STATE_PATH = os.path.join(tmp, "state.json")
    t = FakeTranslator()
    t.create_glossary = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("quota"))
    cache, marks = {}, {}
    tr.translate_missing(["Abriss morgen"], cache, [], glossary_entries=ENTRIES, marks=marks, translator=t)
    assert "glossary" not in t.calls[0] and "Abriss morgen" in cache and marks == {}


def test_stale_entries_are_detected_and_only_redone_on_request():
    tmp = tempfile.mkdtemp()
    tr.CACHE_PATH = os.path.join(tmp, "cache.csv")
    gl.STATE_PATH = os.path.join(tmp, "state.json")
    digest = gl.entries_hash(ENTRIES)
    texts = ["Vorzug nicht möglich", "Abriss ab Juli", "kein Fachbegriff hier", "Vorzug neu"]
    cache = {t: "old" for t in texts}
    marks = {"Vorzug neu": digest}                                   # translated with the current glossary
    assert tr.stale_entries(texts, cache, marks, ENTRIES) == ["Vorzug nicht möglich", "Abriss ab Juli"]
    assert tr.stale_entries(texts, cache, marks, {}) == []

    df = pd.DataFrame({"Comment": ["Vorzug nicht möglich ¦▸ Abriss ab Juli"], "Entry_Languages": ["de|de"],
                       "MATERIAL_NUMBER": ["1"], "VENDOR_NAME": ["ACME"]})
    real = (tr.load_cache, tr.load_marks, tr.save_cache, gl.load_entries)
    try:
        tr.load_cache = lambda: dict(cache)
        tr.load_marks = lambda: dict(marks)
        tr.save_cache = lambda c, m=None: None
        gl.load_entries = lambda path=None: dict(ENTRIES)
        t = FakeTranslator()
        tr.add_translations(df, translator=t)                        # default: nothing is redone
        assert t.calls == []
        tr.add_translations(df, refresh_glossary=True, translator=t)
        assert len(t.calls) == 1 and len(t.calls[0]["glossary"]) > 0
    finally:
        tr.load_cache, tr.load_marks, tr.save_cache, gl.load_entries = real

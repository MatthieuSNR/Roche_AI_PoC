"""Journal entries of a comment cell (data_cleaning.py), abbreviation library (abbreviations.py) and
entry-by-entry translation (translation.py). Synthetic texts only, no network, no API key."""
import os
import sys
import types

import pandas as pd

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
try:
    import langdetect  # noqa: F401
except ImportError:  # the tests must also run where langdetect is not installed
    sys.modules["langdetect"] = types.SimpleNamespace(
        DetectorFactory=types.SimpleNamespace(seed=0),
        detect_langs=lambda text: (_ for _ in ()).throw(Exception("stub")))

import abbreviations as ab  # noqa: E402
import data_cleaning as dc  # noqa: E402
import translation as tr  # noqa: E402


# ------------------------------------------------------------------ entries of a comment cell
def test_signature_chain_is_removed_and_dates_kept():
    p = dc.parse_comment("hochwall, 2026-07-16: hochwall, 2026-07-13: ellmersl, 2026-06-26: Vorzug angefragt")
    assert p["entries"] == ["Vorzug angefragt"]
    assert p["n_authors"] == 2
    assert p["first_entry_date"] == pd.Timestamp("2026-06-26")   # innermost = first written
    assert p["last_entry_date"] == pd.Timestamp("2026-07-16")    # outermost = last saved


def test_several_entries_one_per_line_without_logins():
    p = dc.parse_comment("hottlerj, 2026-03-13: QM Lot aufgelöst\nhottlerj, 2026-03-12: 50 STK in QM Lot")
    assert p["entries"] == ["QM Lot aufgelöst", "50 STK in QM Lot"]
    assert p["comment"] == "QM Lot aufgelöst\n50 STK in QM Lot"
    assert p["n_entries"] == 2 and p["n_authors"] == 1
    assert "hottlerj" not in p["comment"]


def test_typos_in_the_signature_are_tolerated():
    assert dc.parse_comment("hochwall, 20206-07-23: Lieferung KW32")["last_entry_date"] == pd.Timestamp("2026-07-23")
    p = dc.parse_comment("hochwall, 08072026: Mat wird am 10. Juli angeliefert")
    assert p["entries"] == ["Mat wird am 10. Juli angeliefert"]
    assert p["last_entry_date"] == pd.Timestamp("2026-07-08")
    assert dc.parse_comment("crespomj, 2026-06-02 Teillieferung von 50 Stk.")["entries"] == ["Teillieferung von 50 Stk."]
    assert dc.parse_comment("abc12, 2026-06-18 14:35: mit Uhrzeit")["entries"] == ["mit Uhrzeit"]


def test_signature_in_the_middle_of_a_line_opens_a_new_entry():
    p = dc.parse_comment("Vorzug nicht möglich cavegnc, 2026-04-09: Vorzug angefragt")
    assert p["entries"] == ["Vorzug nicht möglich", "Vorzug angefragt"]


def test_unsigned_line_continues_the_previous_entry():
    p = dc.parse_comment("abc12, 2026-01-01: erste Zeile\n@Planning: zweite Zeile\n\nxyz99, 2026-01-02: neu")
    assert p["entries"] == ["erste Zeile @Planning: zweite Zeile", "neu"]


def test_comment_without_signature_and_empty_comments():
    p = dc.parse_comment("kein Stockout")
    assert p["entries"] == ["kein Stockout"] and p["n_authors"] == 0 and pd.isna(p["first_entry_date"])
    assert dc.parse_comment(None) is None
    assert dc.parse_comment("abc12, 2026-01-01:   ") is None


def test_a_date_in_the_text_is_not_a_signature():
    p = dc.parse_comment("abc12, 2026-01-01: Lieferung am 2026-07-01, bestätigt")
    assert p["entries"] == ["Lieferung am 2026-07-01, bestätigt"]


# ------------------------------------------------------------------ abbreviation library
COLUMNS = ab.REQUIRED_COLUMNS


def library(*rows):
    """rows: (abbreviation, match, pattern, applies_to, expansion_de, expansion_en, expand)"""
    table = pd.DataFrame([[a, m, p, ap, de, en, "x", "x", "high", ex, "proposed", ""] for a, m, p, ap, de, en, ex in rows],
                         columns=COLUMNS)
    return ab.Library(table)


LIB = library(
    ("Stk", "ignore_case", "", "both", "Stück", "pieces", "yes"),
    ("AB", "exact", "", "de", "Auftragsbestätigung", "order confirmation", "yes"),
    ("u.", "exact_dot", "", "de", "und", "and", "yes"),
    ("ca.", "ignore_case", "", "de", "circa", "approximately", "yes"),
    ("Purch.", "exact", "", "en", "Einkauf", "purchasing", "yes"),
    ("ETA", "exact", "", "both", "voraussichtliche Ankunft", "estimated time of arrival", "yes"),
    ("LT", "exact", "", "both", "Liefertermin", "lead time", "no"),
    ("KW + number", "regex", r"(?<![A-Za-z])KW\s?(\d{1,2})(?![A-Za-zÄÖÜäöüß0-9])", "both", r"Kalenderwoche \1", r"calendar week \1", "yes"),
    ("i.O.", "ignore_case", "", "de", "in Ordnung", "OK", "yes"),
    ("n.i.O.", "ignore_case", "", "de", "nicht in Ordnung", "not OK", "yes"),
)


def expand(text, lang="de"):
    return ab.expand_text(text, lang, LIB)


def test_case_rules():
    assert expand("AB angefragt, ab Montag") == "Auftragsbestätigung angefragt, ab Montag"   # 'ab' untouched
    assert expand("5 STK, 3 stk, 2 Stk") == "5 Stück, 3 Stück, 2 Stück"
    assert expand("Prüfung u. Korrektur, u Korrektur") == "Prüfung und Korrektur, u Korrektur"   # full stop required


def test_unknown_or_unconfirmed_abbreviations_stay_untouched():
    assert expand("LT vorgezogen") == "LT vorgezogen"           # expand = no
    assert expand("Der Stkabc bleibt") == "Der Stkabc bleibt"    # never inside a longer word


def test_language_of_the_entry_decides():
    assert expand("AB angefragt", "en") == "AB angefragt"        # German-only abbreviation, English entry
    assert expand("ETA 9/14", "en") == "Estimated time of arrival 9/14"
    assert expand("ETA 9/14", "de") == "Voraussichtliche Ankunft 9/14"


def test_numbers_dots_and_sentence_start():
    assert expand("Vorzug KW34, ca. 12 Stk. in Klärung") == "Vorzug Kalenderwoche 34, circa 12 Stück in Klärung"
    assert expand("12 Stk. Lieferung folgt") == "12 Stück. Lieferung folgt"       # the dot ends a sentence
    assert expand("Purch.Group", "en") == "Purchasing Group"
    assert expand("Ware n.i.O., Reichweite i.O.") == "Ware nicht in Ordnung, Reichweite in Ordnung"


def test_expand_comment_works_entry_by_entry():
    out = ab.expand_comment("12 Stk. in QM\nAB angefragt\nETA KW34", ["de", "de", "en"], LIB)
    assert out == "12 Stück in QM\nAuftragsbestätigung angefragt\nEstimated time of arrival calendar week 34"


def test_the_library_file_is_valid_and_consistent():
    assert ab.validate() == []
    table = ab.load_library().table
    assert len(table) > 100
    assert set(table["confidence"]) <= {"high", "medium", "low"}
    assert not table["comment"].str.contains("'").any()   # the committed file carries no excerpt of a real comment
    # only certain meanings are written out
    assert set(table.loc[table["expand"] == "yes", "confidence"]) == {"high"}


def test_real_library_on_typical_entries():
    lib = ab.load_library()
    assert ab.expand_text("3 STK werden am DO von SKR zugestellt", "de", lib) == "3 Stück werden am Donnerstag von SKR zugestellt"
    assert ab.expand_text("PLZ im PIR = 56 Tage", "de", lib) == "Planlieferzeit im Einkaufsinfosatz = 56 Tage"
    assert ab.expand_text("LT erst im Oktober", "de", lib) == "LT erst im Oktober"          # to be confirmed by the planners
    assert ab.expand_text("283 PC werden versendet", "de", lib) == "283 Stück werden versendet"   # no 'Stückück'


# ------------------------------------------------------------------ translation entry by entry
def test_translation_works_entry_by_entry(monkeypatch):
    df = pd.DataFrame({
        "Comment": ["Vorzug angefragt\nsupplier confirmed", "kein Stockout"],
        "Comment_Expanded": ["Vorzug angefragt\nsupplier confirmed", "kein Stockout"],
        "Entry_Languages": ["de|en", "de"],
        "VENDOR_NAME": ["Acme GmbH", None], "MATERIAL_NUMBER": ["10012345", "10099999"],
    })
    cache = {"Vorzug angefragt": "pull-in requested", "kein Stockout": "no stock-out"}
    monkeypatch.setattr(tr, "load_cache", lambda: dict(cache))
    monkeypatch.setattr(tr, "save_cache", lambda c, marks=None: None)
    monkeypatch.setattr(tr, "load_marks", lambda: {})
    out = tr.add_translations(df, dry_run=True)
    assert list(out["Comment_EN"]) == ["pull-in requested\nsupplier confirmed", "no stock-out"]
    assert list(out["comment_language"]) == ["de", "de"]


def test_review_sheet_has_three_simple_columns_and_the_entry_language():
    table = pd.DataFrame([{"abbreviation": "PLZ", "match": "exact", "pattern": "", "applies_to": "both",
                           "expansion_de": "Planlieferzeit", "expansion_en": "planned delivery time",
                           "confidence": "high", "expand": "yes"}])
    library = ab.Library(table)
    df = pd.DataFrame({"Comment": ["PLZ 30 Tage\nPLZ is 30 days"], "Entry_Languages": ["de|en"]})
    sheet = ab.build_sheet(library, df)
    assert sheet.columns.tolist() == ["Abbreviation", "Meaning", "Language"]
    assert sheet.values.tolist() == [["PLZ", "Planlieferzeit", "DE"], ["PLZ", "planned delivery time", "EN"]]

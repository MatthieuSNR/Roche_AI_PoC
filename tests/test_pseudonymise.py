import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from pseudonymise import build_patterns, pseudonymise, restore, vendor_names  # noqa: E402

PATTERNS = build_patterns(vendor_names(pd.Series(["Acme Medical GmbH", "Beta AG"])), ["10012345"])


def test_identifying_elements_are_replaced():
    text = "Acme Medical liefert später, PO 4500123456, Material 10012345, Info: max.muster@roche.com (Roche)"
    safe, mapping = pseudonymise(text, PATTERNS)
    for secret in ["Acme", "4500123456", "10012345", "max.muster", "Roche"]:
        assert secret not in safe
    assert set(k.split("_")[0] for k in mapping) == {"VENDOR", "ID", "MATERIAL", "EMAIL", "COMPANY"}


def test_restore_puts_originals_back():
    text = "Beta AG: Lieferung KW 44 < geplant & bestätigt"
    safe, mapping = pseudonymise(text, PATTERNS)
    assert "&lt;" in safe and "&amp;" in safe  # escaped for DeepL XML handling
    translated = safe.replace("Lieferung", "delivery").replace("geplant", "planned").replace("bestätigt", "confirmed")
    assert restore(translated, mapping) == "Beta AG: delivery KW 44 < planned & confirmed"


def test_same_value_gets_same_placeholder():
    _, mapping = pseudonymise("Beta AG und Beta AG", PATTERNS)
    assert list(mapping) == ["VENDOR_1"]


def test_short_numbers_and_plain_text_untouched():
    safe, mapping = pseudonymise("500 Stk bis 12.11. offen", PATTERNS)
    assert mapping == {} and safe == "500 Stk bis 12.11. offen"


def test_mentions_and_glued_numbers():
    safe, mapping = pseudonymise("@Muster: bitte PO4500123456 prüfen", PATTERNS)
    assert "Muster" not in safe and "4500123456" not in safe
    assert {k.split("_")[0] for k in mapping} == {"PERSON", "ID"}

"""Cloud summary (Mistral API): nothing identifying may leave the machine, and the answer must
come back with the original names. The API is replaced by a fake client (no network, no key)."""
import os
import sys
import types

import pandas as pd

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, SCRIPTS)
if "openai" not in sys.modules:  # the test must also run where openai is not installed
    try:
        import openai  # noqa: F401
    except ImportError:
        sys.modules["openai"] = types.SimpleNamespace(OpenAI=object)
        sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *a, **k: None)

import llm_summary  # noqa: E402
from pseudonymise import PromptPseudonymiser  # noqa: E402

DF = pd.DataFrame({
    "VENDOR_NAME": ["Acme Medical GmbH", "Beta AG", None],
    "MRP_CONTROLLER": ["K12", "K13", "K12"],
    "PURCHASING_GROUP": ["P01", "P02", "P01"],
    "MATERIAL_NUMBER": ["10012345", "10099999", "10012345"],
})
STATS = {
    "total_comments": 3,
    "top_vendors": {"Acme Medical GmbH": {"pct": 60.0}, "Beta AG": {"pct": 40.0}},
    "top_mrp_controllers": {"K12": {"pct": 70.0}},
    "top_purchasing_groups": {"P01": {"pct": 70.0}},
    "top_root_causes_pct": {"Supplier delay": 55.0},
    "comments_by_root_cause": {"Supplier delay": ["Acme Medical liefert später, PO 4500123456, mail max.muster@roche.com"]},
    "top_comments": ["Material 10012345 waiting for Beta AG"],
}
SECRETS = ["Acme", "Beta", "K12", "K13", "P01", "10012345", "4500123456", "max.muster", "roche"]


def fake_client(answer_pieces, sent):
    def create(**kwargs):
        sent.append(kwargs["messages"][0]["content"])
        chunk = lambda t: types.SimpleNamespace(choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content=t))])
        return iter(chunk(t) for t in answer_pieces)
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


def test_prompt_contains_no_real_name():
    p = PromptPseudonymiser(DF)
    prompt = llm_summary.build_prompt(p.apply(STATS), p.apply(STATS["top_comments"]), pseudonymised=True)[0]["content"]
    for secret in SECRETS:
        assert secret.lower() not in prompt.lower(), secret
    assert "VENDOR_1" in prompt and "MRP_1" in prompt and "PGROUP_1" in prompt


def test_same_vendor_same_alias_in_stats_and_comments():
    p = PromptPseudonymiser(DF)
    safe = p.apply(STATS)
    vendor_alias = next(iter(safe["top_vendors"]))
    assert vendor_alias in safe["comments_by_root_cause"]["Supplier delay"][0]  # "Acme Medical" -> same alias
    assert p.restore_text(vendor_alias) == "Acme Medical GmbH"


def test_fresh_pseudonymiser_restarts_numbering():
    base = PromptPseudonymiser(DF)
    base.apply(STATS)
    assert base.fresh().apply({"Beta AG": 1}) == {"VENDOR_1": 1}


def test_cloud_stream_sends_aliases_and_restores_names(monkeypatch):
    sent = []
    p = PromptPseudonymiser(DF)
    alias = next(iter(p.apply(STATS)["top_vendors"]))  # VENDOR_1
    answer = ["- **", alias[:3], alias[3:], "** is late; ", "MRP_", "1 should follow up with ", "VENDOR_2."]
    monkeypatch.setattr(llm_summary, "get_cloud_client", lambda: fake_client(answer, sent))
    text = "".join(llm_summary.stream_summary_cloud(STATS, STATS["top_comments"], PromptPseudonymiser(DF)))
    assert text == "- **Acme Medical GmbH** is late; K12 should follow up with Beta AG."
    for secret in SECRETS:
        assert secret.lower() not in sent[0].lower(), secret


def test_local_prompt_is_unchanged_without_pseudonyms():
    content = llm_summary.build_prompt(STATS, STATS["top_comments"])[0]["content"]
    assert "Acme Medical GmbH" in content and "pseudonyms" not in content

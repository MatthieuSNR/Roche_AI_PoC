import json
from types import SimpleNamespace

from helpers import make_comments, make_snapshots
from roche_poc.llm import prompts, summary, validation
from roche_poc.stats.profile import build_profile


def test_numbers_in_handles_thousands_and_decimals():
    assert validation.numbers_in("1,610 comments, 17.6 percent, week 09") == {1610.0, 17.6, 9.0}


def test_check_numbers_flags_invented_figures():
    facts = {"a": 17.6, "b": 283}
    ok = validation.check_numbers("Share is 17.6 with 283 cases.", facts)
    bad = validation.check_numbers("Share is 18 with 283 cases and 40 more.", facts)
    assert ok["unsupported"] == [] and ok["unsupported_rate"] == 0.0
    assert bad["unsupported"] == [18.0, 40.0]


def test_prompt_is_single_user_message_and_facts_are_compact():
    profile = build_profile(make_snapshots(), make_comments(), "vendor", "Vendor A")
    messages, facts = prompts.build_prompt(profile)
    assert [m["role"] for m in messages] == ["user"]          # no 'system' role (Mistral limit)
    assert "status_timeline" not in json.dumps(facts)         # long series are not sent
    assert len(messages[0]["content"]) < 4000
    assert facts["current"]["status_counts"]["Actual Stock Out"] == 1


def test_generate_summary_with_fake_client_validates_numbers():
    profile = build_profile(make_snapshots(), make_comments(), "vendor", "Vendor A")

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    msg = SimpleNamespace(content=" One stock-out; 999 invented. ")
                    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    result = summary.generate_summary(profile, client=FakeClient())
    assert result.text == "One stock-out; 999 invented."
    assert 999.0 in result.validation["unsupported"]


def test_generate_summary_explains_missing_v1_when_choices_empty():
    profile = build_profile(make_snapshots(), make_comments(), "vendor", "Vendor A")

    class BadClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    return SimpleNamespace(choices=None)

    try:
        summary.generate_summary(profile, client=BadClient())
    except RuntimeError as exc:
        assert "/v1" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

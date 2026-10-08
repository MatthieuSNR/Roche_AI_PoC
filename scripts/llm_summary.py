"""
LLM Summary: generates a natural-language analysis of planner comments
using a LOCAL model served by LM Studio (OpenAI-compatible API).

Architecture: pandas computes the facts (stats dict), the LLM only
interprets them — it never counts or invents figures.

Speed: the prompt contains a COMPACT selection of the statistics (no indentation,
no duplicated figures): about half the tokens of the full stats dict, so the
model starts writing sooner. The answer is streamed (stream_summary) so the
dashboard can show it word by word.
"""



import json
import pandas as pd
from openai import OpenAI

# LM Studio local server — no data leaves the machine
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
MODEL_NAME = "mistralai/mistral-7b-instruct-v0.3"
MAX_TOKENS = 220   # 3 to 4 sentences (~140 tokens), with a margin

def get_client() -> OpenAI:
    """Create an OpenAI-compatible client pointing to the local LM Studio server."""
    return OpenAI(base_url=LM_STUDIO_BASE_URL, api_key="lm-studio", timeout=120.0)  # key is ignored locally


def is_server_available() -> bool:
    """Check that LM Studio is running (avoids a crash in the dashboard)."""
    try:
        get_client().models.list()
        return True
    except Exception:
        return False



def build_facts(stats: dict) -> dict:
    """Compact facts for the prompt. Every key states its unit, so the model does not
    turn a number of comments into a percentage (seen in tests: "+75%" for "+75 comments")."""
    facts = {
        "comments_in_selection": stats.get("total_comments"),
        "share_of_all_comments_pct": stats.get("share_of_all_comments_pct"),
        "comments_with_root_cause_pct": stats.get("root_cause_coverage_pct"),
        "top_root_causes_pct_of_comments": stats.get("top_root_causes_pct"),
        "top_vendors_pct_of_comments": {k: v["pct"] for k, v in stats.get("top_vendors", {}).items()},
        "top_mrp_controllers_pct_of_comments": {k: v["pct"] for k, v in stats.get("top_mrp_controllers", {}).items()},
        "comments_still_open_on_last_snapshot": stats.get("comments_still_open"),
        "comments_still_open_pct": stats.get("comments_still_open_pct"),
        "median_days_a_comment_stays_open": stats.get("median_days_active"),
        "comments_per_week_first_week": stats.get("comments_first_snapshot"),
        "comments_per_week_last_week": stats.get("comments_last_snapshot"),
        "weekly_comment_volume_change_pct": stats.get("trend_pct"),
        "period": f"{stats.get('first_snapshot')} to {stats.get('last_snapshot')}",
        "root_causes_increasing_comments_per_week": stats.get("causes_increasing"),
        "root_causes_decreasing_comments_per_week": stats.get("causes_decreasing"),
        "material_status_number_of_comments": stats.get("material_status_counts"),
        "impact_number_of_comments": stats.get("impact_counts"),
    }
    return {k: v for k, v in facts.items() if v not in (None, {}, [], "None to None")}


def build_prompt(stats: dict, sample_comments: list[str]) -> list[dict]:
    """Build the chat message. NOTE: mistral-7b-instruct-v0.3 does not
    support the 'system' role, so instructions are merged into the user message."""
    instructions = (
        "You are a supply chain analyst at a pharmaceutical company. "
        "You receive PRECOMPUTED statistics and sample planner comments. "
        "Write a concise analysis in 3 to 4 sentences (at most 90 words) covering: "
        "(1) the main issues, (2) how the situation evolved over time, "
        "(3) any emerging risk worth escalating. "
        "Name at most two vendors or MRP controllers; do not list them all. "
        "STRICT RULES: only use the numbers provided in the statistics — "
        "never compute, estimate, or invent figures. A key ending in _pct is a percentage; "
        "every other number is a count of comments, never a percentage. "
        "Do not use markdown formatting. Write in English.\n\n"
    )

    user_content = (
        instructions
        + "Statistics (computed by pandas, JSON):\n"
        + json.dumps(build_facts(stats), separators=(",", ":"))
        + "\n\nSample of the most frequent comments:\n"
        + "\n".join(f"- {c}" for c in sample_comments)
    )

    return [
        {"role": "user", "content": user_content},
    ]


def stream_summary(stats: dict, sample_comments: list[str]):
    """Call the local LLM and yield its analysis piece by piece (streaming)."""
    client = get_client()
    stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=build_prompt(stats, sample_comments),
        temperature=0.2,   # low temperature: factual, less "creative"
        max_tokens=MAX_TOKENS,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def tidy(text: str) -> str:
    """If the answer was cut by MAX_TOKENS, keep it up to its last complete sentence."""
    text = text.strip()
    if text and text[-1] not in ".!?":
        end = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
        if end > 0:
            text = text[:end + 1]
    return text


def generate_summary(stats: dict, sample_comments: list[str]) -> str:
    """Call the local LLM and return its analysis as text."""
    text = tidy("".join(stream_summary(stats, sample_comments)))
    if not text:
        raise ValueError("No response from the LLM.")
    return text

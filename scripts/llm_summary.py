"""
LLM Summary: generates a natural-language analysis of planner comments
using a LOCAL model served by LM Studio (OpenAI-compatible API).

Architecture: pandas computes the facts (stats dict), the LLM only
interprets them — it never counts or invents figures.

The prompt contains a compact selection of the statistics (no indentation, no
duplicated figures) plus the most frequent informative comments of the main root
causes, as evidence. The model writes a structured analysis in 5 fixed sections
(SECTIONS), which the dashboard renders as headings and bullet points. The answer
is streamed (stream_summary) so the dashboard can show it word by word.
"""



import json
import re
import pandas as pd
from openai import OpenAI

# LM Studio local server — no data leaves the machine
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
MODEL_NAME = "mistralai/mistral-7b-instruct-v0.3"
MAX_TOKENS = 750   # structured analysis of 250-350 words (~450 tokens), with a margin
SECTIONS = ["Key findings", "Trend over time", "Where the issues come from",
            "Risks to escalate", "Recommended actions"]

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
        "same_root_causes_pct_of_all_comments": (stats.get("top_root_causes_pct_all")
                                                 if stats.get("share_of_all_comments_pct", 100) < 100 else None),
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
    headings = "\n".join(f"### {h}" for h in SECTIONS)
    instructions = (
        "You are a senior supply chain analyst at a pharmaceutical company, preparing the weekly "
        "Supply Risk Meeting. You receive PRECOMPUTED statistics about planner comments and, for the "
        "main root causes, the most frequent comments written by the planners.\n"
        "Write an in-depth analysis of 250 to 350 words, in English, using EXACTLY these five "
        "headings, in this order:\n"
        f"{headings}\n"
        "Under each heading, write 2 or 3 bullet points starting with '- '. Each bullet is one or two "
        "full sentences. Explain WHY things happen with the planner comments, not only the numbers: "
        "under 'Key findings' and 'Risks to escalate', quote at least one planner comment word for word "
        "in double quotes (copy it exactly from the comments below). Under 'Where the issues come from', name the main vendors and MRP "
        "controllers. Under 'Recommended actions', give concrete next steps for the planners "
        "(no new figures). You may write **bold** for key terms.\n"
        "STRICT RULES: only use the numbers provided in the statistics — never compute, estimate, "
        "or invent figures. A key ending in _pct is a percentage; every other number is a count of "
        "comments, never a percentage. Write nothing before the first heading.\n\n"
    )

    evidence = "\n".join(
        f"[{cause}]\n" + "\n".join(f"- {c}" for c in comments)
        for cause, comments in stats.get("comments_by_root_cause", {}).items() if comments
    )
    user_content = (
        instructions
        + "Statistics (computed by pandas, JSON):\n"
        + json.dumps(build_facts(stats), separators=(",", ":"))
        + "\n\nMost frequent comments of the main root causes:\n"
        + evidence
        + "\n\nMost frequent comments overall:\n"
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
    """If the answer was cut by MAX_TOKENS, keep it up to its last complete sentence
    (also when the sentence ends a bullet point, i.e. is followed by a line break)."""
    text = text.strip()
    if text and text[-1] not in ".!?":
        ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", text)]
        if ends:
            text = text[:ends[-1]]
    return text


def generate_summary(stats: dict, sample_comments: list[str]) -> str:
    """Call the local LLM and return its analysis as text."""
    text = tidy("".join(stream_summary(stats, sample_comments)))
    if not text:
        raise ValueError("No response from the LLM.")
    return text

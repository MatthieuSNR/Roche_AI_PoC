"""
LLM Summary: generates a natural-language analysis of planner comments
using a LOCAL model served by LM Studio (OpenAI-compatible API).

Architecture: pandas computes the facts (stats dict), the LLM only
interprets them — it never counts or invents figures.
"""



import json
import pandas as pd
from openai import OpenAI

# LM Studio local server — no data leaves the machine
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234" 
MODEL_NAME = "mistralai/mistral-7b-instruct-v0.3"

def get_client() -> OpenAI:
    """Create an OpenAI-compatible client pointing to the local LM Studio server."""
    return OpenAI(base_url=LM_STUDIO_BASE_URL, api_key="lm-studio")  # key is ignored locally


def is_server_available() -> bool:
    """Check that LM Studio is running (avoids a crash in the dashboard)."""
    try:
        client = get_client()
        client.models.list()
        return True
    except Exception:
        return False



def build_prompt(stats: dict, sample_comments: list[str]) -> list[dict]:
    """Build the chat message. NOTE: mistral-7b-instruct-v0.3 does not
    support the 'system' role, so instructions are merged into the user message."""
    instructions = (
        "You are a supply chain analyst at a pharmaceutical company. "
        "You receive PRECOMPUTED statistics and sample planner comments. "
        "Write a concise analysis in 3 to 5 sentences covering: "
        "(1) the main issues, (2) how the situation evolved over time, "
        "(3) any emerging risk worth escalating. "
        "STRICT RULES: only use the numbers provided in the statistics — "
        "never compute, estimate, or invent figures. "
        "Do not use markdown formatting. Write in English.\n\n"
    )

    user_content = (
        instructions
        + "Statistics (computed by pandas, JSON):\n"
        + json.dumps(stats, indent=2)
        + "\n\nSample of the most frequent comments:\n"
        + "\n".join(f"- {c}" for c in sample_comments)
    )

    return [
        {"role": "user", "content": user_content},
    ]


def generate_summary(stats: dict, sample_comments: list[str]) -> str:
    """Call the local LLM and return its analysis as text."""
    client = get_client()
    messages = build_prompt(stats, sample_comments)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,   # low temperature: factual, less "creative"
        max_tokens=300,     # we asked for 3-5 sentences
    )
    return response.choices[0].message.content
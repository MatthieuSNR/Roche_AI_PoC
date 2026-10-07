"""Narrative summary of a profile by the local LLM, with automatic number check."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from roche_poc import config
from roche_poc.llm.client import get_client
from roche_poc.llm.prompts import build_prompt
from roche_poc.llm.validation import check_numbers


@dataclass
class SummaryResult:
    text: str
    facts: dict
    validation: dict
    model: str
    seconds: float
    messages: list[dict] = field(repr=False, default_factory=list)


def generate_summary(
    profile: dict,
    client=None,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 350,
) -> SummaryResult:
    """Call the LLM on one profile. ``client`` is injectable (tests, other servers)."""
    client = client or get_client()
    model = model or config.LM_STUDIO_MODEL
    messages, facts = build_prompt(profile)
    start = time.time()
    response = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
    )
    if not getattr(response, "choices", None):
        raise RuntimeError(
            f"Unexpected LM Studio response (is the base URL missing '/v1'?): {response}"
        )
    text = response.choices[0].message.content.strip()
    return SummaryResult(
        text=text, facts=facts, validation=check_numbers(text, facts),
        model=model, seconds=round(time.time() - start, 1), messages=messages,
    )

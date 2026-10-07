"""Automatic check of the figures cited by the LLM.

Limit (to state in the thesis): the check detects numbers that do not exist in the
facts; it cannot detect a correct number attached to the wrong entity.
"""

from __future__ import annotations

import json
import re

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3})")


def numbers_in(text: str) -> set[float]:
    """All numbers of a text as floats (``1,610`` -> 1610, ``09`` -> 9)."""
    return {float(m) for m in _NUMBER.findall(_THOUSANDS.sub("", text))}


def check_numbers(summary: str, facts: dict, tolerance: float = 0.051) -> dict:
    """Compare the numbers of ``summary`` with those of ``facts``.

    A cited number is *supported* if it equals a fact within ``tolerance``. The tolerance
    only absorbs floating-point noise: ``18`` is NOT accepted for ``17.6``.
    """
    allowed = numbers_in(json.dumps(facts, default=str))
    cited = numbers_in(summary)
    unsupported = sorted(c for c in cited if not any(abs(c - a) <= tolerance for a in allowed))
    return {
        "cited": sorted(cited),
        "unsupported": unsupported,
        "unsupported_rate": round(len(unsupported) / len(cited), 3) if cited else 0.0,
    }

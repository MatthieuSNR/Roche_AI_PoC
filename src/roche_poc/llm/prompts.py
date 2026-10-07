"""Prompt construction: profile -> compact facts -> one user message.

``mistral-7b-instruct-v0.3`` rejects the ``system`` role (its chat template raises a
400 error), so the instructions are merged into the single user message.
"""

from __future__ import annotations

import json

from roche_poc import config

INSTRUCTIONS = (
    "You are a supply chain analyst at a pharmaceutical company. "
    "You receive PRECOMPUTED facts about {scope} and recent planner comments. "
    "Write 3 to 5 sentences covering: (1) the current situation and what to watch, "
    "(2) whether it is a punctual or a chronic problem, using the history and persistence facts, "
    "(3) the main root causes and any governance gap (missing root cause or comment), "
    "(4) one risk worth escalating, if any. "
    "STRICT RULES: use only numbers that appear in the facts; never compute, estimate or "
    "invent figures; if a fact is missing, say so. No markdown. Write in English."
)

_SCOPE_LABEL = {
    "vendor": "one supplier (vendor)",
    "mrp_controller": "one MRP controller's portfolio",
    "material": "one material",
}


def profile_to_facts(profile: dict, max_comments: int = 5, max_alerts: int = 5) -> dict:
    """Keep only what the LLM needs (a 7B model drowns in long JSON)."""
    if profile.get("empty"):
        return {"entity": profile.get("entity_id"), "note": "no data for this entity"}
    facts = {
        "entity": profile["entity_id"],
        "level": profile["level"],
        "period": f'{profile["meta"]["first_snapshot"]} to {profile["meta"]["last_snapshot"]}',
        "snapshots_in_history": profile["meta"]["n_snapshots"],
        "current": {
            k: profile["current"][k]
            for k in ("elements", "status_counts", "impact_counts", "critical_share_pct",
                      "portfolio_median_critical_share_pct")
        },
        "critical_share_trend": profile["history"]["critical_share_trend"]["label"],
        "persistence": profile["persistence"],
        "root_causes_top": [
            {"cause": r[config.COL_ROOT_CAUSE], "pct_of_known": r["pct_of_known"], "rows": r["n_rows"]}
            for r in profile["root_causes"]["table"][:3]
        ],
        "critical_without_root_cause_pct": profile["root_causes"]["critical_coverage"]["missing_pct"],
        "alerts": {
            "high": profile["watchlist"]["n_high"],
            "medium": profile["watchlist"]["n_medium"],
            "examples": [a["rule"] + ": " + a["detail"] for a in profile["watchlist"]["alerts"][:max_alerts]],
        },
    }
    if "top_materials" in profile:
        facts["top_materials"] = [
            {"material": m[config.COL_MATERIAL], "status": m["status"], "critical_snapshots": m["n_critical_snapshots"],
             "current_streak": m["current_streak"]}
            for m in profile["top_materials"][:3]
        ]
    comments = [c["text"][:200] for c in profile["recent_comments"][:max_comments] if c.get("text")]
    if comments:
        facts["recent_comments"] = comments
    return facts


def build_prompt(profile: dict) -> tuple[list[dict], dict]:
    """Return the chat messages and the facts they contain (needed for validation)."""
    facts = profile_to_facts(profile)
    instructions = INSTRUCTIONS.format(scope=_SCOPE_LABEL.get(profile.get("level"), "one entity"))
    content = instructions + "\n\nFacts (computed by pandas, JSON):\n" + json.dumps(facts, indent=1, default=str)
    return [{"role": "user", "content": content}], facts

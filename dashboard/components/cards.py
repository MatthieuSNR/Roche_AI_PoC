"""Small display helpers."""

from __future__ import annotations

import streamlit as st

SEVERITY_ICON = {"high": "🔴", "medium": "🟠"}


def metric_row(items: list[tuple[str, object, str | None]]) -> None:
    """Render ``[(label, value, delta_or_None), ...]`` as one row of metrics."""
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        col.metric(label, "—" if value is None else value, delta)


def fmt_pct(value) -> str | None:
    return None if value is None else f"{value:.1f}%"

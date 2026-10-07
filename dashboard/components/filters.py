"""Entity selectors shared by the Supplier / MRP controller / Material pages."""

from __future__ import annotations

import streamlit as st

from roche_poc import config
from components import data_access

LEVEL_TITLES = {"vendor": "Supplier", "mrp_controller": "MRP controller", "material": "Material"}


def entity_selector(snapshots, level: str, key: str | None = None):
    """Selectbox listing entities from riskiest to safest; returns the selected id.

    The selection is stored in ``st.session_state[key]`` so another page can preselect
    an entity (drill-down from a supplier to one of its materials).
    """
    col = config.LEVEL_COLUMNS[level]
    ranking = data_access.get_ranking(data_access.version(), level, snapshots)
    ids = ranking[col].tolist()
    labels = {i: f"{i}" for i in ids}
    if level == "material":
        desc = (
            snapshots.drop_duplicates(config.COL_MATERIAL, keep="last")
            .set_index(config.COL_MATERIAL)[config.COL_MATERIAL_DESC]
        )
        labels = {i: f"{i} — {desc.get(i, '')}" for i in ids}
    if not ids:
        st.warning("No entity in the latest snapshot.")
        st.stop()
    key = key or f"selected_{level}"
    if st.session_state.get(key) not in ids:
        st.session_state[key] = ids[0]
    return st.sidebar.selectbox(
        f"{LEVEL_TITLES[level]} (riskiest first)", ids, format_func=lambda i: labels[i], key=key
    )

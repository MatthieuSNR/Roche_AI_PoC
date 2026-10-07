"""Cached access to the processed tables and to expensive portfolio-wide computations."""

from __future__ import annotations

import streamlit as st

from roche_poc import config
from roche_poc.data.build_tables import load_table
from roche_poc.stats import persistence, profile as profile_mod, watchlist


def _data_version() -> float:
    """File modification time: invalidates the caches when the tables are rebuilt."""
    return config.SNAPSHOTS_PATH.stat().st_mtime if config.SNAPSHOTS_PATH.exists() else 0.0


@st.cache_data(show_spinner="Loading data...")
def _load(version: float):
    return load_table(config.SNAPSHOTS_PATH), load_table(config.COMMENTS_PATH)


def require_tables():
    """Return ``(snapshots, comments)`` or stop the page with a clear instruction."""
    try:
        return _load(_data_version())
    except FileNotFoundError:
        st.error("Processed data not found.")
        st.code("pip install -e .\npython -m roche_poc.data.build_tables", language="bash")
        st.caption("Put the raw snapshot CSVs in data/raw/Snapshot_2026/ first.")
        st.stop()


@st.cache_data(show_spinner="Computing persistence...")
def get_streaks(version: float, _snapshots):
    return persistence.critical_streaks(_snapshots)


@st.cache_data(show_spinner="Computing alerts...")
def get_watchlist(version: float, _snapshots):
    return watchlist.build_watchlist(_snapshots)


@st.cache_data(show_spinner="Ranking...")
def get_ranking(version: float, level: str, _snapshots):
    return watchlist.rank_entities(_snapshots, level, get_watchlist(version, _snapshots))


@st.cache_data(show_spinner="Building profile...")
def get_profile(version: float, level: str, entity_id, _snapshots, _comments):
    return profile_mod.build_profile(
        _snapshots, _comments, level, entity_id, streaks=get_streaks(version, _snapshots)
    )


@st.cache_data
def get_overview(version: float, _snapshots):
    return profile_mod.portfolio_overview(_snapshots)


def version() -> float:
    return _data_version()

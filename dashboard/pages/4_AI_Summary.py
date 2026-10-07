"""AI summary: the LLM only phrases what pandas has already computed."""

import json

import streamlit as st

from components import data_access
from components.filters import LEVEL_TITLES, entity_selector
from roche_poc import config
from roche_poc.llm.client import is_server_available
from roche_poc.llm.summary import generate_summary

st.set_page_config(page_title="AI summary", layout="wide")
st.title("AI summary (local LLM)")
st.caption("Generated locally through LM Studio: no data leaves the machine. "
           "All figures come from the statistics layer; every number in the text is checked against them.")

snapshots, comments = data_access.require_tables()
level = st.sidebar.radio("Level", list(LEVEL_TITLES), format_func=LEVEL_TITLES.get)
entity = entity_selector(snapshots, level, key=f"ai_{level}")
profile = data_access.get_profile(data_access.version(), level, entity, snapshots, comments)

if profile.get("empty"):
    st.info("No data for this selection.")
    st.stop()
if not is_server_available():
    st.warning(f"LM Studio not reachable at {config.LM_STUDIO_BASE_URL}. Start the server (Developer tab) and load the model.")
    st.stop()

if st.button("Generate summary"):
    with st.spinner("The local model is analysing the profile..."):
        try:
            st.session_state["ai_result"] = (level, entity, generate_summary(profile))
        except Exception as exc:  # network / model errors must not crash the page
            st.error(f"LLM call failed: {exc}")

saved = st.session_state.get("ai_result")
if saved:
    s_level, s_entity, result = saved
    if (s_level, s_entity) != (level, entity):
        st.caption(f"⚠️ Summary generated for {s_entity}, not for the current selection.")
    st.write(result.text)
    bad = result.validation["unsupported"]
    if bad:
        st.warning(f"Numbers not found in the facts: {bad} ({result.validation['unsupported_rate']:.0%} of cited numbers).")
    else:
        st.success("All cited numbers are present in the facts.")
    st.caption(f"{result.model} · {result.seconds}s")
    with st.expander("Facts sent to the model"):
        st.code(json.dumps(result.facts, indent=1, default=str), language="json")

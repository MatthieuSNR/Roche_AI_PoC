"""Portfolio view: where to look first."""

import streamlit as st

from components import cards, charts, data_access
from components.entity_view import _show
from roche_poc import config

st.set_page_config(page_title="Material Availability — Portfolio", layout="wide")
st.title("Material Availability: portfolio overview")

snapshots, comments = data_access.require_tables()
ver = data_access.version()
ov = data_access.get_overview(ver, snapshots)

counts = ov["status_counts"]
cards.metric_row([
    ("Latest snapshot", ov["last_snapshot"], None),
    ("MRP elements", ov["elements"], f"{ov['materials']} materials"),
    ("Critical share", cards.fmt_pct(ov["critical_share_pct"]), None),
    ("Actual stock-outs", counts[config.STATUS_ACTUAL], None),
    ("High / medium alerts", f"{ov['alerts_high']} / {ov['alerts_medium']}", None),
])
cov = ov["root_cause_coverage"]
if cov["missing_pct"]:
    st.warning(f"Governance: {cov['missing_pct']}% of critical elements have no root cause.")

st.subheader("Status over time")
_show(charts.status_timeline_chart(ov["status_timeline"]))

left, right = st.columns(2)
for col, level, title in ((left, "vendor", "Riskiest suppliers"), (right, "mrp_controller", "Riskiest MRP controllers")):
    with col:
        st.subheader(title)
        ranking = data_access.get_ranking(ver, level, snapshots).head(10)
        st.dataframe(ranking, hide_index=True, use_container_width=True)
st.caption("Ranking: high-severity alerts, then actual stock-outs, then critical share (latest snapshot). "
           "Use the pages on the left to open a supplier, an MRP controller or a material.")

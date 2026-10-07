"""One rendering for every level: the same profile dictionary, the same layout."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from roche_poc import config
from components import cards, charts


def _show(fig) -> None:
    st.pyplot(fig)
    plt.close(fig)


def render_entity(profile: dict, level: str, open_material_page: str | None = None) -> None:
    if profile.get("empty"):
        st.info("No data for this selection.")
        return
    meta, cur = profile["meta"], profile["current"]
    st.caption(
        f"History: {meta['first_snapshot']} → {meta['last_snapshot']} · "
        f"{meta['n_snapshots']} snapshots · {meta['n_materials']} material(s)"
    )
    if not meta["in_latest_snapshot"]:
        st.warning("This entity does not appear in the latest snapshot: current figures are empty.")

    # 1) At-a-glance banner ------------------------------------------------- #
    counts, impact = cur["status_counts"], cur["impact_counts"]
    critical = counts[config.STATUS_POTENTIAL] + counts[config.STATUS_ACTUAL]
    bench = cur["portfolio_median_critical_share_pct"]
    delta = None
    if cur["critical_share_pct"] is not None and bench is not None:
        delta = f"{cur['critical_share_pct'] - bench:+.1f} pts vs portfolio median"
    cards.metric_row([
        ("Critical elements", critical, cards.fmt_pct(cur["critical_share_pct"])),
        ("Actual stock-outs", counts[config.STATUS_ACTUAL], None),
        ("Production / Market impact", impact.get(config.IMPACT_PRODUCTION, 0) + impact.get(config.IMPACT_MARKET, 0), None),
        ("High-severity alerts", profile["watchlist"]["n_high"], f"{profile['watchlist']['n_medium']} medium"),
        ("Chronic materials", profile["persistence"]["chronic_materials"],
         f"max streak {profile['persistence']['max_current_streak']}"),
    ])
    if delta:
        st.caption(f"Critical share: {delta}" + (
            f" · riskier than {cur['percentile_vs_portfolio']:.0f}% of peers" if cur["percentile_vs_portfolio"] is not None else ""))

    # 2) Points to watch + history ----------------------------------------- #
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Points to watch")
        alerts = profile["watchlist"]["alerts"]
        if alerts:
            table = pd.DataFrame(alerts)
            table.insert(0, "", table["severity"].map(cards.SEVERITY_ICON))
            keep = [c for c in ("", config.COL_MATERIAL, "rule", "detail") if c in table.columns]
            st.dataframe(table[keep], hide_index=True, use_container_width=True, height=260)
            if profile["watchlist"]["n_high"] + profile["watchlist"]["n_medium"] > len(alerts):
                st.caption(f"Showing the first {len(alerts)} alerts.")
        else:
            st.success("No alert on the latest snapshot.")
    with right:
        st.subheader("History")
        _show(charts.status_timeline_chart(profile["history"]["status_timeline"]))

    st.markdown("**Is it punctual or chronic?**")
    trend = profile["history"]["critical_share_trend"]
    _show(charts.critical_share_chart(
        [{config.COL_SNAPSHOT: r.get("_snap", r.get(config.COL_SNAPSHOT)), "critical_share": r["critical_share"]}
         for r in profile["history"]["critical_share_series"]],
        trend["label"],
    ))
    if trend["label"] == "insufficient data":
        st.caption("Fewer than %d snapshots: no trend is claimed." % config.MIN_POINTS_FOR_TREND)

    # 3) Root causes -------------------------------------------------------- #
    st.subheader("Root causes")
    cov = profile["root_causes"]["critical_coverage"]
    if cov["missing_pct"]:
        st.warning(f"{cov['missing_pct']}% of critical elements in the latest snapshot have no root cause "
                   f"({cov['critical_rows'] - cov['with_root_cause']} of {cov['critical_rows']}).")
    c1, c2 = st.columns([1, 1])
    with c1:
        _show(charts.root_cause_chart(profile["root_causes"]["table"]))
    with c2:
        st.dataframe(pd.DataFrame(profile["root_causes"]["table"]), hide_index=True, use_container_width=True)
        st.caption("Percentages are shares of rows WITH a root cause. Counts are element-snapshots (exposure).")

    # 4) Drill-down --------------------------------------------------------- #
    if level == "material":
        st.subheader("Suppliers of this material")
        st.dataframe(pd.DataFrame(profile["related_vendors"]), hide_index=True, use_container_width=True)
        if profile.get("stockout_dates"):
            st.caption("Recent projected stock-out dates: " + ", ".join(profile["stockout_dates"]))
    else:
        st.subheader("Materials to look at first")
        mats = pd.DataFrame(profile["top_materials"])
        if mats.empty:
            st.caption("No material in the latest snapshot.")
        else:
            st.dataframe(mats, hide_index=True, use_container_width=True)
            if open_material_page:
                pick = st.selectbox("Open a material", mats[config.COL_MATERIAL].tolist(), key=f"pick_{level}")
                if st.button("Open in Material page"):
                    st.session_state["selected_material"] = pick
                    st.switch_page(open_material_page)

    # 5) Qualitative context ------------------------------------------------- #
    st.subheader("Recent planner comments")
    comments = pd.DataFrame(profile["recent_comments"])
    if comments.empty:
        st.caption("No comment for this selection.")
    else:
        st.dataframe(comments, hide_index=True, use_container_width=True,
                     column_config={"text": st.column_config.TextColumn("comment", width="large")})

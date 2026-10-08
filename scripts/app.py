import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import os
import sys
import threading
import time

# Make scripts/ importable so we can reuse our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from llm_summary import generate_summary, is_server_available
from stats_engine import compute_stats, root_cause_sources, weekly_active, NO_ROOT_CAUSE
import ui



st.set_page_config(
    page_title="Roche AI PoC - NLP Insights",
    layout="wide",
)
ui.apply_style()  # Look of the Roche ION Material Availability dashboard (scripts/ui.py)


# Load cleaned data (built by scripts/data_cleaning.py, translated by scripts/translation.py)
@st.cache_data
def load_data():
    return pd.read_csv("data/cleaned_comments.csv")

df = load_data().copy()

# --- Create combined display labels for filters ---

# Material: description + number (e.g., "Syringe 10ml - 3000123456")
df["MATERIAL_LABEL"] = (
    df["MATERIAL_DESC"].fillna("No description")
    + " — "
    + df["MATERIAL_NUMBER"].astype("int64").astype(str)
)

# Vendor: name + account number (e.g., "B. Braun — 50012345")
df["VENDOR_LABEL"] = (
    df["VENDOR_NAME"].fillna("Unknown vendor")
    + " — "
    + df["VENDOR_ACCOUNT_NUMBER"].astype("Int64").astype(str).replace("<NA>", "no vendor")
)

df["MRP_CONTROLLER"] = df["MRP_CONTROLLER"].fillna("Unknown")

# Convert dates to datetime for proper sorting and filtering
for col in ["Snapshot_Date", "First_Seen", "Last_Seen"]:
    df[col] = pd.to_datetime(df[col], errors="coerce")



# Title + navigation menu (each entry scrolls down to its section; all sections follow each other)
SECTIONS = [
    ("overview", "🏠 Overview"),
    ("filtered-comments", "💬 Filtered Comments"),
    ("top-root-causes", "🔥 Top Root Causes"),
    ("frequent-comments", "📊 Most Frequent Comments"),
    ("root-cause-details", "🔎 Comments for a Root Cause"),
    ("trends", "📈 Root Cause Trends"),
    ("key-statistics", "📋 Key Statistics"),
    ("ai-summary", "🤖 AI Summary"),
]
SECTION_TITLES = dict(SECTIONS)
ui.top_bar("ION Material Availability", "Insights from Planner Comments", SECTIONS)

# Filters
st.sidebar.header("Filters")


# Vendor filter: user can search by name OR account number
vendor_options = ["All"] + sorted(df["VENDOR_LABEL"].unique().tolist())
selected_vendor_label = st.sidebar.selectbox("Select Vendor:", vendor_options)
vendor_name_only = selected_vendor_label.split(" — ")[0] if selected_vendor_label != "All" else "All"


# MRP controller filter
mrp_options = ["All"] + sorted(df["MRP_CONTROLLER"].unique().tolist())
selected_mrp = st.sidebar.selectbox("Select MRP Controller:", mrp_options)


# Material filter: user can search by number OR description
material_options = ["All"] + sorted(df["MATERIAL_LABEL"].unique().tolist())
selected_material_label = st.sidebar.selectbox("Select Material:", material_options)


# Root cause filter: user can select from the unique root causes
selected_root_cause = st.sidebar.selectbox(
    "Select Root Cause:", ["All"] + sorted(df["Root_Cause"].dropna().unique().tolist())
)




# --- Timeframe filter (Part A: record the user's choice only) ---
st.sidebar.subheader("Timeframe")
timeframe_option = st.sidebar.selectbox(
    "Select period:",
    ["All snapshots", "Last 4 weeks", "Last 8 weeks", "Last 16 weeks", "Custom period"],
)

# If "Custom period" is selected, show a date range picker
start_ts, end_ts = None, None
if timeframe_option == "Custom period":
    min_date = df["First_Seen"].min().date()
    max_date = df["Last_Seen"].max().date()
    date_range = st.sidebar.date_input(
        "Date range:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    # date_input returns a tuple only when BOTH dates are selected
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_ts = pd.to_datetime(date_range[0])
        end_ts = pd.to_datetime(date_range[1])
st.sidebar.caption("A comment is in the period if it was visible in the dashboard at least once during it.")


# Filter data
filtered_df = df.copy()
if selected_vendor_label != "All":
    filtered_df = filtered_df[filtered_df["VENDOR_LABEL"] == selected_vendor_label]
if selected_mrp != "All":
    filtered_df = filtered_df[filtered_df["MRP_CONTROLLER"] == selected_mrp]
if selected_material_label != "All":
    filtered_df = filtered_df[filtered_df["MATERIAL_LABEL"] == selected_material_label]
if selected_root_cause != "All":
    filtered_df = filtered_df[filtered_df["Root_Cause"] == selected_root_cause]

# --- Timeframe filter (Part B: apply the choice to filtered_df) ---
# A comment stays visible for many days: keep it if [First_Seen, Last_Seen] overlaps the period
if timeframe_option == "Custom period":
    if start_ts is not None:
        filtered_df = filtered_df[
            (filtered_df["Last_Seen"] >= start_ts)
            & (filtered_df["First_Seen"] <= end_ts)
        ]
elif timeframe_option.startswith("Last"):
    weeks = int(timeframe_option.split(" ")[1])
    latest_snapshot = df["Last_Seen"].max()
    cutoff = latest_snapshot - pd.Timedelta(weeks=weeks)
    filtered_df = filtered_df[filtered_df["Last_Seen"] >= cutoff]
# "All snapshots" → no filtering needed


# Name of the current selection, used in chart titles
selection_parts = [p for p in [vendor_name_only, selected_mrp, selected_material_label.split(" — ")[0],
                               selected_root_cause] if p != "All"]
selection_name = " / ".join(selection_parts) if selection_parts else "All comments"

# Compute all statistics ONCE (used by all sections and the AI Summary)
stats = compute_stats(filtered_df, df)

# ================= OVERVIEW =================
ui.section("overview", "🏠 Overview — " + selection_name)

# --- Headline: where the selection stands among all comments ---
if stats["total_comments"] > 0:
    st.markdown(
        f"**{selection_name}**: {stats['total_comments']} comments "
        f"(**{stats['share_of_all_comments_pct']}%** of all {len(df)} comments) · "
        f"{stats['root_cause_coverage_pct']}% have a root cause · "
        f"{stats['comments_still_open']} still visible on the last snapshot ({stats['latest_snapshot']})"
    )

# --- Material status tiles (ION colour code) ---
# Each comment is written on an MRP element (a material / purchase order line of the ION
# workbench). The tiles count the comments by the ION status of that element.
ui.panel_header("Material status of the commented items")
ui.status_tiles(stats.get("material_status_counts", {}), stats["total_comments"])
st.caption("Each comment is written on an item of the ION workbench (a material / purchase order line). "
           "The tiles show the status of that item the last time the comment was visible, e.g. how many "
           "comments concern items in Actual Stock Out.")
ui.status_definitions()

# --- Sections: all analyses follow each other on one page (menu at the top to jump) ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = [st.container() for _ in range(7)]



# ================= SECTION 1: Filtered Comments =================

with tab1:
    ui.section("filtered-comments", SECTION_TITLES["filtered-comments"])
    show_original = st.checkbox("Show the original (German) comment next to the translation")
    columns = ["Comment_EN"] + (["Comment"] if show_original else []) + [
        "First_Seen", "Last_Seen", "Days_Active", "STOCKOUT_DATE", "MATERIAL_STATUS",
        "Root_Cause", "Impact", "VENDOR_NAME", "MRP_CONTROLLER", "MATERIAL_LABEL"]
    st.dataframe(
        filtered_df.sort_values("Last_Seen", ascending=False)[columns]
        .rename(columns={
            "Comment_EN": "Comment (EN)",
            "Comment": "Original comment",
            "First_Seen": "First seen",
            "Last_Seen": "Last seen",
            "Days_Active": "Days visible",
            "STOCKOUT_DATE": "Stockout Date",
            "MATERIAL_STATUS": "Material Status",
            "Root_Cause": "Root Cause",
            "VENDOR_NAME": "Vendor Name",
            "MRP_CONTROLLER": "MRP Controller",
            "MATERIAL_LABEL": "Material"
        })

        .assign(**{"First seen": lambda d: d["First seen"].dt.strftime("%Y-%m-%d"),
                   "Last seen": lambda d: d["Last seen"].dt.strftime("%Y-%m-%d"),
                   "Stockout Date": lambda d: pd.to_datetime(d["Stockout Date"], errors="coerce").dt.strftime("%Y-%m-%d")}),

        use_container_width=True,
        height=500,
    column_config={
        "Comment (EN)": st.column_config.TextColumn(width="large"),
        "Original comment": st.column_config.TextColumn(width="large"),
    },
    hide_index=True,
        )
    st.caption("One row = one comment on one material of one vendor. "
               "'Days visible' = for how many days the comment stayed in the dashboard.")


# ================= SECTION 2: Top Root Causes =================

with tab2:
    ui.section("top-root-causes", SECTION_TITLES["top-root-causes"])

    top_n_causes = st.radio(
        "Show:", options=["Top 5", "Top 10", "Top 20"], horizontal=True,
        key="radio_top_causes",
    )
    n_causes = int(top_n_causes.split(" ")[1])

    # 1. Comments without a root cause are counted apart (they are not a cause)
    total_comments = len(filtered_df)
    no_cause_count = int(filtered_df["Root_Cause"].isna().sum())

    # 2. Count root causes in the FILTERED data (respects all filters)
    root_cause_counts = filtered_df["Root_Cause"].value_counts().head(n_causes)

    if root_cause_counts.empty:
        st.info("No root cause filled in for the current filters.")
    else:
        # 3. Build the color gradient: green (low) -> yellow -> orange -> red (high)
        #    We use a custom colormap and scale each bar by its count relative to the max
        colormap = mcolors.LinearSegmentedColormap.from_list(
            "severity", ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]  # green, yellow, orange, red
        )
        max_count = root_cause_counts.max()
        colors = [colormap(count / max_count) for count in root_cause_counts.values]

        # 4. Plot (horizontal bars: easier to read long root cause names)
        fig, ax = plt.subplots(figsize=(10, max(4, len(root_cause_counts) * 0.5)))
        bars = ax.barh(root_cause_counts.index[::-1], root_cause_counts.values[::-1],
                    color=colors[::-1])
        ax.set_title(f"Top {n_causes} Root Causes — {selection_name}")
        ax.set_xlabel("Number of Comments")

        # Add the count and the share of the selection's comments at the end of each bar
        for bar, count in zip(bars, root_cause_counts.values[::-1]):
            ax.text(bar.get_width() + max_count * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{count} ({count / total_comments * 100:.1f}%)", va="center")

        st.pyplot(fig)
        st.caption(f"% = share of the {total_comments} comments of the selection. "
                   f"{no_cause_count} comments ({no_cause_count / total_comments * 100:.1f}%) have no root cause.")

        # 5. Compare with all comments: is a root cause over-represented in this selection?
        if selection_parts:
            all_total = len(df)
            compare_df = pd.DataFrame({
                "Root Cause": root_cause_counts.index,
                f"% of {selection_name} comments": (root_cause_counts.values / total_comments * 100).round(1),
                "% of all comments": [round((df["Root_Cause"] == c).sum() / all_total * 100, 1)
                                      for c in root_cause_counts.index],
            })
            compare_df["Difference (pts)"] = (compare_df.iloc[:, 1] - compare_df.iloc[:, 2]).round(1)
            st.markdown("**Compared with all comments**")
            st.dataframe(compare_df, use_container_width=True, hide_index=True)

        # 6. Show the percentage share
        # Split: top N causes as individual slices, rest grouped as "Other"
        all_cause_counts = filtered_df["Root_Cause"].value_counts()
        top_counts = all_cause_counts.head(n_causes)
        other_count = all_cause_counts.iloc[n_causes:].sum()

        pie_labels = top_counts.index.tolist()
        pie_values = top_counts.values.tolist()
        if other_count > 0:
            pie_labels.append("Other")
            pie_values.append(other_count)

        fig_pie, ax_pie = plt.subplots(figsize=(8, 8))
        ax_pie.pie(
            pie_values,
            labels=pie_labels,
            autopct="%1.1f%%",       # Show percentage on each slice
            startangle=90,
            colors=plt.cm.Set3.colors[:len(pie_values)],  # Distinct colors
        )
        ax_pie.set_title(f"Root Cause Share — {selection_name}")
        st.pyplot(fig_pie)

        # Keep the caption only for the "Other" context
        st.caption(f"Pie: share among the comments WITH a root cause. "
                   f"'Other' = all remaining root causes beyond the Top {n_causes} ({other_count} comments).")


# ================= SECTION 3: Most Frequent Comments =================

with tab3:
    ui.section("frequent-comments", SECTION_TITLES["frequent-comments"])

    top_n_comments = st.radio(
        "Show:", options=["Top 5", "Top 10", "Top 20"], horizontal=True,
        key="radio_top_comments",
    )
    n_comments = int(top_n_comments.split(" ")[1])

    # Count identical comments in the filtered data (same text on several materials / vendors)
    top_comments_df = (
        filtered_df.groupby("Comment_EN")
        .agg(Occurrences=("Comment_EN", "size"),
             Materials=("MATERIAL_NUMBER", "nunique"),
             Vendors=("VENDOR_NAME", "nunique"),
             Days_visible=("Days_Active", "sum"),
             Root_Cause=("Root_Cause", lambda s: s.mode().iloc[0] if s.notna().any() else NO_ROOT_CAUSE))
        .sort_values(["Occurrences", "Days_visible"], ascending=False)
        .head(n_comments)
        .reset_index()
    )
    top_comments_df.insert(2, "% of comments", (top_comments_df["Occurrences"] / max(len(filtered_df), 1) * 100).round(1))

    # Display as a clean table
    st.dataframe(
        top_comments_df.rename(columns={"Comment_EN": "Comment (EN)", "Days_visible": "Days visible (total)",
                                        "Root_Cause": "Main root cause"}),
        use_container_width=True, hide_index=True,
        column_config={"Comment (EN)": st.column_config.TextColumn(width="large")},
    )
    st.caption("Occurrences = number of (material, vendor) the same comment was written for. "
               "Days visible = total days these comments stayed in the dashboard.")


# ================= SECTION 4: Comments for a Root Cause =================

with tab4:
    ui.section("root-cause-details", SECTION_TITLES["root-cause-details"])
    # Show all root causes of the filtered data (not just top N)
    causes_available = filtered_df["Root_Cause"].value_counts().index.tolist()
    if causes_available:
        selected_cause_for_details = st.selectbox(
            "Select a root cause:", causes_available
        )
        details = filtered_df[filtered_df["Root_Cause"] == selected_cause_for_details]
        st.caption(f"{len(details)} comments = {len(details) / len(filtered_df) * 100:.1f}% "
                   f"of the comments of the selection.")

        # Where does this root cause come from? (vendors and MRP controllers)
        col_v, col_m = st.columns(2)
        with col_v:
            st.markdown("**Vendors with this root cause**")
            st.dataframe(root_cause_sources(filtered_df, selected_cause_for_details, "VENDOR_NAME")
                         .rename(columns={"VENDOR_NAME": "Vendor"}),
                         use_container_width=True, hide_index=True)
        with col_m:
            st.markdown("**MRP controllers with this root cause**")
            st.dataframe(root_cause_sources(filtered_df, selected_cause_for_details, "MRP_CONTROLLER")
                         .rename(columns={"MRP_CONTROLLER": "MRP Controller"}),
                         use_container_width=True, hide_index=True)

        st.markdown("**Comments**")
        st.dataframe(
            details.sort_values("Last_Seen", ascending=False)[
                ["Comment_EN", "Days_Active", "VENDOR_LABEL", "MRP_CONTROLLER", "MATERIAL_LABEL"]].rename(
                columns={
                    "Comment_EN": "Comment (EN)",
                    "Days_Active": "Days visible",
                    "VENDOR_LABEL": "Vendor",
                    "MRP_CONTROLLER": "MRP Controller",
                    "MATERIAL_LABEL": "Material",
                }
            ),
            use_container_width=True, hide_index=True,
            column_config={"Comment (EN)": st.column_config.TextColumn(width="large")},
        )
    else:
        st.info("No comments with a root cause match the current filters.")



# ================= SECTION 5: Root Cause Trends Over Time =================
with tab5:
    ui.section("trends", SECTION_TITLES["trends"])

    # 1. Count comments visible each week, per root cause — pandas does the math
    #    (snapshots are daily: a weekly view is readable and a comment open for
    #    5 weeks counts in each of those weeks)
    trend_data = weekly_active(filtered_df.dropna(subset=["Root_Cause"]), by="Root_Cause")

    if trend_data.empty:
        st.info("No data to display for the current filters.")
    else:
        # 2. Limit to the top 5 root causes of the filtered data (readable chart)
        top_5_causes = filtered_df["Root_Cause"].value_counts().head(5).index
        trend_top5 = trend_data[[c for c in top_5_causes if c in trend_data.columns]]

        # 3. Plot: one line per root cause
        fig, ax = plt.subplots(figsize=(12, 6))
        for cause in trend_top5.columns:
            ax.plot(
                trend_top5.index,
                trend_top5[cause],
                marker="o",
                label=cause,
            )
        ax.set_title(f"Root Cause Evolution — {selection_name}")
        ax.set_xlabel("Week")
        ax.set_ylabel("Comments visible during the week")
        ax.legend(title="Root Cause", bbox_to_anchor=(1.02, 1), loc="upper left")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

        # 4. Simple numeric insight (computed by pandas, not hallucinated!)
        ui.panel_header("Key Numbers")
        if "comments_first_snapshot" in stats:
            first, last = stats["comments_first_snapshot"], stats["comments_last_snapshot"]
            st.metric(
                f"Comments visible (week of {stats['first_snapshot']} → week of {stats['last_snapshot']})",
                f"{first} → {last}",
                delta=f"{last - first:+d}",
            )



# ================= SECTION 6: Key Statistics =================
with tab6:
    ui.section("key-statistics", SECTION_TITLES["key-statistics"])

    # Handle the empty case first (avoid crashes on very narrow filters)
    if stats["total_comments"] == 0:
        st.info("No comments match the current filters. Relax some filters to see statistics.")
    else:
        # --- Row 1: headline metrics ---
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Comments", stats["total_comments"],
                      help="One comment on one material of one vendor")
            st.caption(f"{stats['share_of_all_comments_pct']}% of all comments")

        with col2:
            st.metric("With a root cause", f"{stats['root_cause_coverage_pct']}%")
            st.caption(f"Vendors: {stats['vendor_count']} · MRP controllers: {stats['mrp_controller_count']} "
                       f"· Materials: {stats['material_count']}")

        with col3:
            st.metric("Median days visible", f"{stats['median_days_active']:.0f}",
                      delta=(f"{stats['median_days_active'] - stats['median_days_active_all']:+.0f} vs all"
                             if stats['median_days_active'] != stats['median_days_active_all'] else None),
                      delta_color="inverse")
            st.caption(f"{stats['comments_still_open']} still visible on {stats['latest_snapshot']} "
                       f"({stats['comments_still_open_pct']}%)")

        with col4:
            if "trend_pct" in stats:
                st.metric(
                    "Weekly comment volume",
                    f"{stats['comments_first_snapshot']} → {stats['comments_last_snapshot']}",
                    delta=f"{stats['trend_pct']:+.1f}%",
                    delta_color="inverse",
                )
            if "german_comments_pct" in stats:
                st.caption(f"{stats['german_comments_pct']}% written in German (translated)")

        # --- Row 2: time window ---
        if "first_snapshot" in stats:
            st.caption(
                f"Period: weeks of {stats['first_snapshot']} → {stats['last_snapshot']}"
            )

        # --- Root cause table with counts AND percentages (vs all comments) ---
        st.markdown("**Top 5 Root Causes**")
        cause_df = pd.DataFrame({
            "Root Cause": list(stats["top_root_causes"].keys()),
            "Comments": list(stats["top_root_causes"].values()),
            "% of selection": list(stats["top_root_causes_pct"].values()),
            "% of all comments": list(stats["top_root_causes_pct_all"].values()),
        })
        st.dataframe(cause_df, use_container_width=True, hide_index=True)

        # --- Who is concerned: vendors and MRP controllers ---
        col_v, col_m = st.columns(2)
        with col_v:
            st.markdown("**Top Vendors (share of the comments)**")
            st.dataframe(pd.DataFrame([{"Vendor": k, "Comments": v["comments"], "%": v["pct"]}
                                       for k, v in stats["top_vendors"].items()]),
                         use_container_width=True, hide_index=True)
        with col_m:
            st.markdown("**Top MRP Controllers (share of the comments)**")
            st.dataframe(pd.DataFrame([{"MRP Controller": k, "Comments": v["comments"], "%": v["pct"]}
                                       for k, v in stats["top_mrp_controllers"].items()]),
                         use_container_width=True, hide_index=True)

        # --- Rising vs falling causes (the most valuable insight!) ---
        col_a, col_b = st.columns(2)
        if stats.get("causes_increasing"):
            with col_a:
                st.markdown("**📈 Increasing (first → last week)**")
                for cause, delta in stats["causes_increasing"].items():
                    st.caption(f"- {cause}: **+{delta}**")
        if stats.get("causes_decreasing"):
            with col_b:
                st.markdown("**📉 Decreasing (first → last week)**")
                for cause, delta in stats["causes_decreasing"].items():
                    st.caption(f"- {cause}: **{delta}**")

        # --- Material status and impact ---
        col_c, col_d = st.columns(2)
        if "material_status_counts" in stats:
            with col_c:
                st.markdown("**Material Status**")
                for status, count in stats["material_status_counts"].items():
                    st.caption(f"- {status}: {count} ({count / stats['total_comments'] * 100:.1f}%)")
        if "impact_counts" in stats:
            with col_d:
                st.markdown("**Impact**")
                for impact, count in stats["impact_counts"].items():
                    st.caption(f"- {impact}: {count} ({count / stats['total_comments'] * 100:.1f}%)")



# ================= SECTION 7: AI Summary =================
with tab7:
    ui.section("ai-summary", SECTION_TITLES["ai-summary"] + " (local LLM)")
    st.caption("Generated locally via LM Studio: no data leaves the machine. "
               "All figures are computed by pandas; the LLM only interprets them.")

    filter_key = (selected_vendor_label, selected_mrp, selected_material_label,
                  selected_root_cause, timeframe_option)

    if stats["total_comments"] == 0:
        st.info("No comments match the current filters.")
    elif not is_server_available():
        st.warning("LM Studio server not reachable. Start it (Developer tab) and load the model.")
    else:
        if st.button("Generate summary", type="primary"):
            # The LLM runs in a background thread while the loading screen shows the analysis
            # steps. Every value shown on the screen is a real figure of the current selection.
            result = {}

            def call_llm():
                try:
                    result["text"] = generate_summary(stats, stats["top_comments"])
                except Exception as e:  # shown in the dashboard below
                    result["error"] = e

            worker = threading.Thread(target=call_llm, daemon=True)
            worker.start()

            top_cause = next(iter(stats.get("top_root_causes_pct", {}).items()), None)
            n_days = (df["Last_Seen"].max() - df["First_Seen"].min()).days + 1
            steps = [
                {"text": "Loading planner comments from the daily snapshots",
                 "value": f"{len(df):,} comments · {n_days} days"},
                {"text": "Applying filters", "value": f"{selection_name} → {stats['total_comments']:,} comments"},
                {"text": "Reading translated comments (DE → EN)",
                 "value": f"{stats.get('german_comments_pct', 0)}% originally in German"},
                {"text": "Cross-referencing vendors and MRP controllers",
                 "value": f"{stats.get('vendor_count', 0)} vendors · {stats.get('mrp_controller_count', 0)} MRP controllers"},
                {"text": "Ranking root causes",
                 "value": f"top: {top_cause[0]} ({top_cause[1]}%)" if top_cause else "no root cause filled in"},
                {"text": "Measuring how long issues stay open",
                 "value": f"median {stats.get('median_days_active', 0):.0f} days · {stats.get('comments_still_open', 0)} still open"},
                {"text": "Detecting week-by-week trends",
                 "value": f"{stats.get('comments_first_snapshot', '–')} → {stats.get('comments_last_snapshot', '–')} comments/week"},
                {"text": "Writing the summary with the local language model", "value": "on-device"},
            ]
            sample = (filtered_df["Comment_EN"].dropna().astype(str).str.slice(0, 110)
                      .sample(min(40, filtered_df["Comment_EN"].notna().sum()), random_state=0).tolist())

            step_ms = 850
            min_seconds = step_ms * (len(steps) - 1) / 1000 + 0.6  # let the animation reach the last step
            screen = st.empty()
            with screen.container():
                ui.ai_loading_screen(steps, total=stats["total_comments"],
                                     sub="Statistics computed by pandas · local LLM (LM Studio)",
                                     comments=sample, step_ms=step_ms)
            started = time.time()
            while worker.is_alive() or time.time() - started < min_seconds:
                time.sleep(0.2)
            screen.empty()

            if "error" in result:
                st.error(f"LLM call failed: {result['error']}")
            else:
                st.session_state["ai_summary"] = (
                    filter_key, result["text"], selection_name, stats["total_comments"],
                    time.strftime("%Y-%m-%d %H:%M"))

        saved = st.session_state.get("ai_summary")
        if saved:
            if saved[0] != filter_key:
                st.caption("⚠️ Summary generated with different filters.")
            ui.ai_result(saved[1], f"{saved[2]} · based on {saved[3]} comments · generated {saved[4]} "
                                   f"with a local LLM · figures computed by pandas")

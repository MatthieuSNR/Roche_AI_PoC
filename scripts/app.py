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
from llm_summary import (stream_summary, stream_summary_cloud, tidy, is_server_available,
                         is_cloud_configured, build_prompt, MISTRAL_MODEL)
from pseudonymise import PromptPseudonymiser
from stats_engine import compute_stats, root_cause_sources, weekly_active, NO_ROOT_CAUSE
import ui



# Browser tab icon: the Roche logo in blue (assets/favicon.png), an emoji if the file is missing
FAVICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "favicon.png")

st.set_page_config(
    page_title="Roche AI PoC - NLP Insights",
    page_icon=FAVICON_PATH if os.path.exists(FAVICON_PATH) else "🔷",
    layout="wide",
)
ui.apply_style()  # Look of the Roche ION Material Availability dashboard (scripts/ui.py)


# Password gate for remote access (tunnel from this Mac): active only when APP_PASSWORD is set in .env
def check_password():
    password = os.getenv("APP_PASSWORD", "")
    if not password or st.session_state.get("authenticated"):
        return
    st.title("Material Availability – Insights from Planner Comments")
    entered = st.text_input("Password", type="password")
    if entered:
        if entered == password:
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Wrong password.")
    st.stop()

check_password()


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
df["PURCHASING_GROUP"] = df["PURCHASING_GROUP"].fillna("Unknown")

# Impact filter: the data holds two spellings per level ("Production" and
# "Production (Stop&Go/...)"), so the filter works on the four official levels
# (ION: None / Logistics / Production / Market) plus the comments with no impact entered.
IMPACT_FILTER_OPTIONS = ["Market", "Production", "Logistics", "None (no impact)", "Not assessed"]


def impact_level(value):
    """Map a raw Impact label to one of the filter options."""
    if pd.isna(value):
        return "Not assessed"
    label = str(value).strip().lower()
    for prefix, level in (("market", "Market"), ("production", "Production"),
                          ("logistic", "Logistics"), ("none", "None (no impact)")):
        if label.startswith(prefix):
            return level
    return str(value).strip()


df["Impact_Level"] = df["Impact"].map(impact_level)

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
ui.top_bar("Material Availability", "Insights from Planner Comments", SECTIONS)
ui.scroll_spy()  # menu entry of the section on screen in blue

# Filters
st.sidebar.header("Filters")


# Filters, from top to bottom: MRP controller, purchasing group (organisational
# responsibility), vendor, material, root cause, impact.
# Every filter accepts several values (e.g. an MRP controller and the colleagues they back up);
# an empty filter means "All".

def multi_filter(label, options):
    return st.sidebar.multiselect(label, options, placeholder="All")


# MRP controller filter
selected_mrp = multi_filter("Select MRP Controller:", sorted(df["MRP_CONTROLLER"].unique().tolist()))


# Purchasing group filter (organisational responsibility, the first filter of the ION dashboard)
selected_pgroup = multi_filter("Select Purchasing Group:", sorted(df["PURCHASING_GROUP"].unique().tolist()))


# Vendor filter: user can search by name OR account number
selected_vendor_label = multi_filter("Select Vendor:", sorted(df["VENDOR_LABEL"].unique().tolist()))


# Material filter: user can search by number OR description
selected_material_label = multi_filter("Select Material:", sorted(df["MATERIAL_LABEL"].unique().tolist()))


# Root cause filter: user can select from the unique root causes
selected_root_cause = multi_filter("Select Root Cause:", sorted(df["Root_Cause"].dropna().unique().tolist()))


# Impact filter (severity first: Market, Production, Logistics, None, Not assessed)
impacts_present = set(df["Impact_Level"].unique())
impact_options = [o for o in IMPACT_FILTER_OPTIONS if o in impacts_present] \
    + sorted(impacts_present - set(IMPACT_FILTER_OPTIONS))
selected_impact = multi_filter("Select Impact:", impact_options)




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
for column, selected in [("MRP_CONTROLLER", selected_mrp), ("PURCHASING_GROUP", selected_pgroup),
                         ("VENDOR_LABEL", selected_vendor_label), ("MATERIAL_LABEL", selected_material_label),
                         ("Root_Cause", selected_root_cause), ("Impact_Level", selected_impact)]:
    if selected:
        filtered_df = filtered_df[filtered_df[column].isin(selected)]

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
def selection_label(values, short=False):
    """Chart-title label of one filter: the value, or "first value +N" when several are selected."""
    names = [v.split(" — ")[0] for v in values] if short else list(values)
    return names[0] if len(names) == 1 else f"{names[0]} +{len(names) - 1}" if names else None

selection_parts = [p for p in [selection_label(selected_mrp), selection_label(selected_pgroup),
                               selection_label(selected_vendor_label, short=True),
                               selection_label(selected_material_label, short=True),
                               selection_label(selected_root_cause), selection_label(selected_impact)] if p]
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
        "Root_Cause", "Impact", "VENDOR_NAME", "PURCHASING_GROUP", "MRP_CONTROLLER", "MATERIAL_LABEL"]
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
            "PURCHASING_GROUP": "Purchasing Group",
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

        # Bar chart and pie side by side (Streamlit stacks the columns on a small screen).
        # Both figures have the SAME height and widths in the same ratio as the columns (3:2),
        # so they are displayed at the same height and grow / shrink with the screen.
        col_bar, col_pie = st.columns([3, 2], gap="medium")
        chart_height = max(3.6, len(root_cause_counts) * 0.26)

        # 4. Plot (horizontal bars: easier to read long root cause names)
        fig, ax = plt.subplots(figsize=(6, chart_height), facecolor="white")
        bars = ax.barh(root_cause_counts.index[::-1], root_cause_counts.values[::-1],
                    color=colors[::-1])
        ax.set_title(f"Top {n_causes} Root Causes — {selection_name}")
        ax.set_xlabel("Number of Comments")
        ax.set_xlim(0, max_count * 1.22)  # room for the labels at the end of the bars

        # Add the count and the share of the selection's comments at the end of each bar
        for bar, count in zip(bars, root_cause_counts.values[::-1]):
            ax.text(bar.get_width() + max_count * 0.01, bar.get_y() + bar.get_height() / 2,
                    f"{count} ({count / total_comments * 100:.1f}%)", va="center", fontsize=8)
        fig.tight_layout()

        with col_bar:
            st.pyplot(fig, bbox_inches=None)  # keep the exact figure size (same height as the pie)
            st.caption(f"% = share of the {total_comments} comments of the selection. "
                       f"{no_cause_count} comments ({no_cause_count / total_comments * 100:.1f}%) have no root cause.")

        # 5. Show the percentage share
        # Split: top N causes as individual slices, rest grouped as "Other"
        all_cause_counts = filtered_df["Root_Cause"].value_counts()
        top_counts = all_cause_counts.head(n_causes)
        other_count = all_cause_counts.iloc[n_causes:].sum()

        pie_labels = top_counts.index.tolist()
        pie_values = top_counts.values.tolist()
        if other_count > 0:
            pie_labels.append("Other")
            pie_values.append(other_count)

        # Pie on top, legend below (labels on the slices overlap when there are many causes)
        fig_pie = plt.figure(figsize=(3.85, chart_height), facecolor="white")  # 3.85: same height as the bars once in the cards
        legend_rows = -(-len(pie_labels) // 2)
        legend_frac = (0.15 + legend_rows * 0.15) / chart_height
        title_frac = 0.35 / chart_height
        ax_pie = fig_pie.add_axes([0.02, legend_frac + 0.02, 0.96, 1 - legend_frac - title_frac - 0.03])
        palette = plt.cm.tab20.colors if len(top_counts) > 12 else plt.cm.Set3.colors
        pie_colors = list(palette[:len(top_counts)]) + (["#BDBDBD"] if other_count > 0 else [])  # "Other" in grey
        wedges, _, _ = ax_pie.pie(
            pie_values,
            autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",  # Show percentage on the large slices
            startangle=90,
            counterclock=False,
            colors=pie_colors,  # Distinct colors
            wedgeprops={"edgecolor": "white", "linewidth": 1},
            textprops={"fontsize": 8},
        )
        fig_pie.suptitle(f"Root Cause Share — {selection_name}", fontsize=10, fontweight="bold",
                         y=1 - 0.08 / chart_height)
        legend_labels = [l if len(l) <= 26 else l[:25] + "…" for l in pie_labels]
        fig_pie.legend(wedges, legend_labels, loc="lower center", bbox_to_anchor=(0.5, 0.01),
                       ncol=2, fontsize=7, frameon=False, handlelength=1, columnspacing=1)

        with col_pie:
            st.pyplot(fig_pie, bbox_inches=None)
            # Keep the caption only for the "Other" context
            st.caption(f"Share among the comments WITH a root cause. "
                       f"'Other' = all remaining root causes beyond the Top {n_causes} ({other_count} comments).")

        # 6. Compare with all comments: is a root cause over-represented in this selection?
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
        # (short column names so that the three tables fit side by side)
        short_names = {f"% of '{selected_cause_for_details}' comments": "% of this cause",
                       "% of this entity's comments": "% of its comments"}
        for column, (by, label) in zip(st.columns(3), [("VENDOR_NAME", "Vendor"),
                                                        ("PURCHASING_GROUP", "Purchasing Group"),
                                                        ("MRP_CONTROLLER", "MRP Controller")]):
            with column:
                st.markdown(f"**{label}s with this root cause**")
                st.dataframe(root_cause_sources(filtered_df, selected_cause_for_details, by)
                             .rename(columns={by: label, **short_names}),
                             use_container_width=True, hide_index=True)
        st.caption("% of this cause = share of the comments with this root cause; "
                   "% of its comments = share of the vendor's (group's, controller's) comments.")

        st.markdown("**Comments**")
        st.dataframe(
            details.sort_values("Last_Seen", ascending=False)[
                ["Comment_EN", "Days_Active", "VENDOR_LABEL", "PURCHASING_GROUP", "MRP_CONTROLLER", "MATERIAL_LABEL"]].rename(
                columns={
                    "Comment_EN": "Comment (EN)",
                    "Days_Active": "Days visible",
                    "VENDOR_LABEL": "Vendor",
                    "PURCHASING_GROUP": "Purchasing Group",
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
        # 2. Root causes to display: the top 5 of the filtered data by default,
        #    the user can add or remove any root cause of the selection
        causes_by_frequency = filtered_df["Root_Cause"].value_counts().index.tolist()
        selected_trend_causes = st.multiselect(
            "Root causes to display (default: the 5 most frequent):",
            options=causes_by_frequency,
            default=causes_by_frequency[:5],
            key="trend_causes",
        )
        trend_selected = trend_data[[c for c in selected_trend_causes if c in trend_data.columns]]

        if trend_selected.empty:
            st.info("Select at least one root cause to display.")
        else:
            # 3. Plot: one line per root cause (20 distinct colours when many are selected)
            fig, ax = plt.subplots(figsize=(12, 6))
            line_colors = plt.cm.tab20.colors if len(trend_selected.columns) > 8 else None
            for i, cause in enumerate(trend_selected.columns):
                ax.plot(
                    trend_selected.index,
                    trend_selected[cause],
                    marker="o",
                    label=cause,
                    color=line_colors[i % 20] if line_colors else None,
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
            st.caption(f"Vendors: {stats['vendor_count']} · Purchasing groups: {stats['purchasing_group_count']} "
                       f"· MRP controllers: {stats['mrp_controller_count']} "
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
        for column, (key, label) in zip(st.columns(3), [("top_vendors", "Vendor"),
                                                         ("top_purchasing_groups", "Purchasing Group"),
                                                         ("top_mrp_controllers", "MRP Controller")]):
            with column:
                st.markdown(f"**Top {label}s (share of the comments)**")
                st.dataframe(pd.DataFrame([{label: k, "Comments": v["comments"], "%": v["pct"]}
                                           for k, v in stats[key].items()]),
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
# Two ways to write the same analysis from the same pandas statistics:
#  - Cloud: Mistral API, works once the app is deployed; names are pseudonymised before sending.
#  - Local: LM Studio on this machine (unchanged), no data leaves the computer.
@st.cache_resource(show_spinner=False)
def pseudonymiser_template(n_rows: int):
    """Entity lists (vendors, materials...) are built once; each request gets a fresh() copy."""
    return PromptPseudonymiser(df)


def render_ai_summary(mode: str):
    """Button + loading screen + streamed answer, for mode 'cloud' or 'local'."""
    cloud = mode == "cloud"
    label = f"Mistral API ({MISTRAL_MODEL})" if cloud else "local LLM (LM Studio)"
    session_key = "ai_summary_cloud" if cloud else "ai_summary"

    filter_key = tuple(tuple(v) for v in (selected_mrp, selected_pgroup, selected_vendor_label,
                  selected_material_label, selected_root_cause, selected_impact)) + (timeframe_option,)

    pseudonymise_on = False
    if cloud:
        st.caption("Generated by the Mistral API. Prices and volumes are never sent: the request only contains "
                   "aggregated statistics and a few planner comments. All figures are computed by pandas; "
                   "the LLM only interprets them.")
        pseudonymise_on = st.checkbox(
            "Pseudonymise vendors, MRP controllers, purchasing groups and material numbers before sending "
            "(recommended)", value=True, key="pseudonymise_cloud")
    else:
        st.caption("Generated locally via LM Studio: no data leaves the machine. "
                   "All figures are computed by pandas; the LLM only interprets them.")

    if stats["total_comments"] == 0:
        st.info("No comments match the current filters.")
        return
    if cloud and not is_cloud_configured():
        st.warning("No Mistral API key found. Add MISTRAL_API_KEY to the .env file (local) or to the "
                   "Streamlit secrets (deployed app).")
        return
    if not cloud and not is_server_available():
        st.warning("LM Studio server not reachable. Start it (Developer tab) and load the model.")
        return

    pseudonymiser = pseudonymiser_template(len(df)).fresh() if (cloud and pseudonymise_on) else None
    if cloud:
        with st.expander("What is sent to the API?"):
            sent_stats = pseudonymiser.apply(stats) if pseudonymiser else stats
            sent_comments = pseudonymiser.apply(stats["top_comments"]) if pseudonymiser else stats["top_comments"]
            st.code(build_prompt(sent_stats, sent_comments, pseudonymised=pseudonymiser is not None)[0]["content"],
                    language="text")

    if st.button("Generate summary", type="primary", key=f"generate_{mode}"):
        # The LLM runs in a background thread while the loading screen shows the analysis
        # steps. Every value shown on the screen is a real figure of the current selection.
        # The answer is streamed: it appears word by word as soon as the model writes.
        result = {"parts": [], "done": False}

        def call_llm():
            try:
                if cloud:
                    # fresh pseudonymiser: the aliases of this request only
                    pieces = stream_summary_cloud(
                        stats, stats["top_comments"], pseudonymiser_template(len(df)).fresh() if pseudonymise_on else None)
                else:
                    pieces = stream_summary(stats, stats["top_comments"])
                for piece in pieces:
                    result["parts"].append(piece)
            except Exception as e:  # shown in the dashboard below
                result["error"] = e
            finally:
                result["done"] = True

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
            {"text": "Writing the summary with the Mistral API" if cloud else "Writing the summary with the local language model",
             "value": ("pseudonymised" if pseudonymise_on else "not pseudonymised") if cloud else "on-device"},
        ]
        sample = (filtered_df["Comment_EN"].dropna().astype(str).str.slice(0, 110)
                  .sample(min(40, filtered_df["Comment_EN"].notna().sum()), random_state=0).tolist())

        step_ms = 850
        min_seconds = step_ms * (len(steps) - 1) / 1000 + 0.6  # let the animation reach the last step
        screen = st.empty()
        with screen.container():
            ui.ai_loading_screen(steps, total=stats["total_comments"],
                                 sub=f"Statistics computed by pandas · {label}",
                                 comments=sample, step_ms=step_ms)
        started = time.time()
        # Loading screen until the model starts writing (and at least the animation length)
        while (not result["parts"] and not result["done"]) or time.time() - started < min_seconds:
            time.sleep(0.2)
        screen.empty()

        # Then the text appears as it is written
        live = st.empty()
        meta = f"{selection_name} · writing with the {label}…"
        while not result["done"]:
            live.markdown(ui.ai_result_html("".join(result["parts"]) + " ▌", meta), unsafe_allow_html=True)
            time.sleep(0.15)
        live.empty()

        text = tidy("".join(result["parts"]))  # up to the last complete sentence
        if "error" in result:
            st.error(f"LLM call failed: {result['error']}")
        elif not text:
            st.error("LLM call failed: empty answer.")
        else:
            st.session_state[session_key] = (
                filter_key, text, selection_name, stats["total_comments"],
                time.strftime("%Y-%m-%d %H:%M"), label)

    saved = st.session_state.get(session_key)
    if saved:
        if saved[0] != filter_key:
            st.caption("⚠️ Summary generated with different filters.")
        ui.ai_result(saved[1], f"{saved[2]} · based on {saved[3]} comments · generated {saved[4]} "
                               f"with {saved[5]} · figures computed by pandas")


with tab7:
    ui.section("ai-summary", SECTION_TITLES["ai-summary"])
    tab_cloud, tab_local = st.tabs(["☁️ Cloud (Mistral API)", "💻 Local (LM Studio)"])
    with tab_cloud:
        render_ai_summary("cloud")
    with tab_local:
        render_ai_summary("local")

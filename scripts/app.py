import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np


st.set_page_config(
    page_title="Roche AI PoC - NLP Insights",
    layout="wide", 
)


# Load cleaned data
@st.cache_data
def load_data():
    return pd.read_csv("data/cleaned_comments.csv")

df = load_data()

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
    + df["VENDOR_ACCOUNT_NUMBER"].astype(str)
)

# Convert Snapshot Date to datetime for proper sorting and filtering
df["Snapshot_Date"] = pd.to_datetime(df["Snapshot_Date"], errors="coerce")



# Title
st.title("Material availability dashboard: Insights from Planner Comments")

# Filters
st.sidebar.header("Filters")


# Vendor filter: user can search by name OR account number
vendor_options = ["All"] + sorted(df["VENDOR_LABEL"].unique().tolist())
selected_vendor_label = st.sidebar.selectbox("Select Vendor:", vendor_options)
vendor_name_only = selected_vendor_label.split(" — ")[0] if selected_vendor_label != "All" else "All"


# Material filter: user can search by number OR description
material_options = ["All"] + sorted(df["MATERIAL_LABEL"].unique().tolist())
selected_material_label = st.sidebar.selectbox("Select Material:", material_options)


# Root cause filter: user can select from the unique root causes
selected_root_cause = st.sidebar.selectbox("Select Root Cause:", ["All"] + df["Root_Cause"].unique().tolist())


    
    
# --- Timeframe filter (Part A: record the user's choice only) ---
st.sidebar.subheader("Timeframe")
timeframe_option = st.sidebar.selectbox(
    "Select period:",
    ["All snapshots", "Last 4 weeks", "Last 8 weeks", "Last 16 weeks", "Custom period"],
)

# If "Custom period" is selected, show a date range picker
start_ts, end_ts = None, None
if timeframe_option == "Custom period":
    min_date = df["Snapshot_Date"].min().date()
    max_date = df["Snapshot_Date"].max().date()
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
    

# Filter data
filtered_df = df.copy()
if selected_vendor_label != "All":
    filtered_df = filtered_df[filtered_df["VENDOR_LABEL"] == selected_vendor_label]
if selected_material_label != "All":
    filtered_df = filtered_df[filtered_df["MATERIAL_LABEL"] == selected_material_label]
if selected_root_cause != "All":
    filtered_df = filtered_df[filtered_df["Root_Cause"] == selected_root_cause]

# --- Timeframe filter (Part B: apply the choice to filtered_df) ---
if timeframe_option == "Custom period":
    if start_ts is not None:
        filtered_df = filtered_df[
            (filtered_df["Snapshot_Date"] >= start_ts)
            & (filtered_df["Snapshot_Date"] <= end_ts)
        ]
elif timeframe_option.startswith("Last"):
    weeks = int(timeframe_option.split(" ")[1])
    latest_snapshot = df["Snapshot_Date"].max()
    cutoff = latest_snapshot - pd.Timedelta(weeks=weeks)
    filtered_df = filtered_df[filtered_df["Snapshot_Date"] >= cutoff]
# "All snapshots" → no filtering needed

# --- Tabs: organize the analysis into navigable sections ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 Filtered Comments",
    "🔥 Top Root Causes",
    "📊 Most Frequent Comments",
    "🔎 Comments for a Root Cause",
    "📈 Root Cause Trends Over Time"
])



# ================= TAB 1: Filtered Comments =================

with tab1:
    st.subheader("Filtered Comments")
    st.dataframe(
        filtered_df[["Comment_EN", "Snapshot_Date", "STOCKOUT_DATE", "MATERIAL_STATUS", "Root_Cause", "Impact", "VENDOR_NAME", "MATERIAL_LABEL"]]
        .rename(columns={
            "Comment_EN": "Comment (EN)",
            "Snapshot_Date": "Snapshot Date",
            "STOCKOUT_DATE": "Stockout Date",
            "MATERIAL_STATUS": "Material Status",
            "Root_Cause": "Root Cause",
            "VENDOR_NAME": "Vendor Name",
            "MATERIAL_LABEL": "Material"
        })
        
        .assign(**{"Snapshot Date": lambda d: d["Snapshot Date"].dt.strftime("%Y-%m-%d"),
                   "Stockout Date": lambda d: pd.to_datetime(d["Stockout Date"], errors="coerce").dt.strftime("%Y-%m-%d")}),
        
        use_container_width=True,
        height=500,
    column_config={
        "Comment (EN)": st.column_config.TextColumn(width="large"),
    },
    hide_index=True,
        )


# ================= TAB 2: Top Root Causes =================

with tab2:
    st.subheader("Top Root Causes")
    
    top_n_causes = st.radio(
        "Show:", options=["Top 5", "Top 10", "Top 20"], horizontal=True,
        key="radio_top_causes",
    )
    n_causes = int(top_n_causes.split(" ")[1])

    # 2. Count root causes in the FILTERED data (respects the vendor filter)
    root_cause_counts = filtered_df["Root_Cause"].value_counts().head(n_causes)

    # 3. Build the color gradient: green (low) -> yellow -> orange -> red (high)
    #    We use a custom colormap and scale each bar by its count relative to the max
    colormap = mcolors.LinearSegmentedColormap.from_list(
        "severity", ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]  # green, yellow, orange, red
    )
    max_count = root_cause_counts.max()
    colors = [colormap(count / max_count) for count in root_cause_counts.values]

    # 4. Plot (horizontal bars: easier to read long root cause names)
    fig, ax = plt.subplots(figsize=(10, max(4, n_causes * 0.5)))
    bars = ax.barh(root_cause_counts.index[::-1], root_cause_counts.values[::-1],
                color=colors[::-1])
    ax.set_title(f"Top {n_causes} Root Causes" + (f" — {vendor_name_only}" if vendor_name_only != "All" else " — All Vendors"))
    ax.set_xlabel("Number of Comments")

    # Add the count at the end of each bar
    for bar, count in zip(bars, root_cause_counts.values[::-1]):
        ax.text(bar.get_width() + max_count * 0.01, bar.get_y() + bar.get_height() / 2,
                str(count), va="center")

    st.pyplot(fig)

    # 5. Show the percentage share 
    total_comments = len(filtered_df)
    if total_comments > 0:
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
        ax_pie.set_title(f"Root Cause Share — {vendor_name_only}")
        st.pyplot(fig_pie)

        # Keep the caption only for the "Other" context
        st.caption(f"'Other' = all remaining root causes beyond the Top {n_causes} ({other_count} comments).")


# ================= TAB 3: Most Frequent Comments =================

with tab3:
    st.subheader("Most Frequent Comments")
    
    top_n_comments = st.radio(
        "Show:", options=["Top 5", "Top 10", "Top 20"], horizontal=True,
        key="radio_top_comments",
    )
    n_comments = int(top_n_comments.split(" ")[1])

    # Count identical comments in the filtered data
    comment_counts = filtered_df["Comment_EN"].value_counts().head(n_comments)

    # Display as a clean table
    top_comments_df = comment_counts.reset_index()
    top_comments_df.columns = ["Comment (EN)", "Occurrences"]
    st.dataframe(top_comments_df, use_container_width=True)


# ================= TAB 4: Comments for a Root Cause =================

with tab4:
    st.subheader("🔎 Comments for a Specific Root Cause")
    # Show all root causes of the filtered data (not just top N)
    causes_available = filtered_df["Root_Cause"].unique().tolist()
    if causes_available:
        selected_cause_for_details = st.selectbox(
            "Select a root cause:", causes_available
        )
        details = filtered_df[filtered_df["Root_Cause"] == selected_cause_for_details]
        st.dataframe(
            details[["Comment_EN", "VENDOR_LABEL", "MATERIAL_LABEL"]].rename(
                columns={
                    "Comment_EN": "Comment (EN)",
                    "VENDOR_LABEL": "Vendor",
                    "MATERIAL_LABEL": "Material",
                }
            ).head(20),
            use_container_width=True,
        )
    else:
        st.info("No comments match the current filters.")
        


# ================= TAB 5: Root Cause Trends Over Time =================
with tab5:
    st.subheader("📈 Root Cause Trends Over Time")

    # 1. Convert Snapshot_Date to datetime for proper sorting
    #filtered_df["Snapshot_Date"] = pd.to_datetime(
    #    filtered_df["Snapshot_Date"], errors="coerce"
    #)

    # 2. Count comments per (snapshot date, root cause) — pandas does the math
    trend_data = (
        filtered_df
        .dropna(subset=["Snapshot_Date", "Root_Cause"])
        .groupby(["Snapshot_Date", "Root_Cause"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )

    if trend_data.empty:
        st.info("No data to display for the current filters.")
    else:
        # 3. Limit to the top 5 root causes of the filtered data (readable chart)
        top_5_causes = filtered_df["Root_Cause"].value_counts().head(5).index
        trend_top5 = trend_data[[c for c in top_5_causes if c in trend_data.columns]]

        # 4. Plot: one line per root cause
        fig, ax = plt.subplots(figsize=(12, 6))
        for cause in trend_top5.columns:
            ax.plot(
                trend_top5.index,
                trend_top5[cause],
                marker="o",
                label=cause,
            )
        ax.set_title(f"Root Cause Evolution — {vendor_name_only}")
        ax.set_xlabel("Snapshot Date")
        ax.set_ylabel("Number of Comments")
        ax.legend(title="Root Cause", bbox_to_anchor=(1.02, 1), loc="upper left")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

        # 5. Simple numeric insight (computed by pandas, not hallucinated!)
        st.subheader("Key Numbers")
        total_by_date = trend_data.sum(axis=1)
        if len(total_by_date) >= 2:
            first, last = total_by_date.iloc[0], total_by_date.iloc[-1]
            change = last - first
            st.metric(
                "Total comments (first → last snapshot)",
                f"{first} → {last}",
                delta=f"{change:+d}",
            )
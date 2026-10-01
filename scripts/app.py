import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# Load cleaned data
@st.cache_data
def load_data():
    return pd.read_csv("data/cleaned_comments.csv")

df = load_data()

# --- Create combined display labels for filters ---

# Material: description + number (e.g., "Syringe 10ml - 3000123456")
df["MATERIAL_LABEL"] = (
    df["MATERIAL_DESC"].fillna("No description"
    + " — "
    + df["MATERIAL_NUMBER"].astype(str))
)

# Vendor: name + account number (e.g., "B. Braun — 50012345")
df["VENDOR_LABEL"] = (
    df["VENDOR_NAME"].fillna("Unknown vendor")
    + " — "
    + df["VENDOR_ACCOUNT_NUMBER"].astype(str)
)


# Title
st.title("🔍 Roche AI PoC: NLP Insights from Planner Comments")

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

# Filter data
filtered_df = df.copy()
if selected_vendor_label != "All":
    filtered_df = filtered_df[filtered_df["VENDOR_LABEL"] == selected_vendor_label]
if selected_material_label != "All":
    filtered_df = filtered_df[filtered_df["MATERIAL_LABEL"] == selected_material_label]
if selected_root_cause != "All":
    filtered_df = filtered_df[filtered_df["Root_Cause"] == selected_root_cause]

# Display filtered comments
st.subheader("Filtered Comments")
st.dataframe(
    filtered_df[["Comment_EN", "Root_Cause", "VENDOR_NAME", "MATERIAL_LABEL"]]
    .rename(columns={
        "Comment_EN": "Comment (EN)",
        "Root_Cause": "Root Cause",
        "VENDOR_NAME": "Vendor Name",
        "MATERIAL_LABEL": "Material"
    }),
    use_container_width=True
    )


# --- Top N Root Causes chart ---

st.subheader("🔥 Top Root Causes")

# 1. Let the user choose Top 5 or Top 10
top_n = st.radio("Show:", options=["Top 5", "Top 10"], horizontal=True)
n = int(top_n.split(" ")[1])  # Extract 5 or 10

# 2. Count root causes in the FILTERED data (respects the vendor filter)
root_cause_counts = filtered_df["Root_Cause"].value_counts().head(n)

# 3. Build the color gradient: green (low) -> yellow -> orange -> red (high)
#    We use a custom colormap and scale each bar by its count relative to the max
colormap = mcolors.LinearSegmentedColormap.from_list(
    "severity", ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"]  # green, yellow, orange, red
)
max_count = root_cause_counts.max()
colors = [colormap(count / max_count) for count in root_cause_counts.values]

# 4. Plot (horizontal bars: easier to read long root cause names)
fig, ax = plt.subplots(figsize=(10, max(4, n * 0.5)))
bars = ax.barh(root_cause_counts.index[::-1], root_cause_counts.values[::-1],
               color=colors[::-1])
ax.set_title(f"Top {n} Root Causes" + (f" — {vendor_name_only}" if vendor_name_only != "All" else " — All Vendors"))
ax.set_xlabel("Number of Comments")

# Add the count at the end of each bar
for bar, count in zip(bars, root_cause_counts.values[::-1]):
    ax.text(bar.get_width() + max_count * 0.01, bar.get_y() + bar.get_height() / 2,
            str(count), va="center")

st.pyplot(fig)

# 5. Show the percentage share (useful insight: "X% of this vendor's comments")
total_comments = len(filtered_df)
if total_comments > 0:
    st.caption("Share of total comments:")
    for cause, count in root_cause_counts.items():
        st.caption(f"- **{cause}**: {count} comments ({count / total_comments * 100:.1f}%)")


# --- Top N Recurring Comments ---
st.subheader("💬 Most Frequent Comments")

# Count identical comments in the filtered data
comment_counts = filtered_df["Comment_EN"].value_counts().head(n)

# Display as a clean table
top_comments_df = comment_counts.reset_index()
top_comments_df.columns = ["Comment (EN)", "Occurrences"]
st.dataframe(top_comments_df, use_container_width=True)



# --- Example comments for a selected root cause ---
st.subheader("🔎 Comments for a Specific Root Cause")
selected_cause_for_details = st.selectbox(
    "Select a root cause to inspect:", root_cause_counts.index.tolist()
)
details = filtered_df[filtered_df["Root_Cause"] == selected_cause_for_details]
st.dataframe(details[["Comment_EN", "VENDOR_NAME", "MATERIAL_NUMBER"]].head(10),
             use_container_width=True)
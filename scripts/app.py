import streamlit as st
import pandas as pd

# Load cleaned data
@st.cache_data
def load_data():
    return pd.read_csv("datad/cleaned_comments.csv")

df = load_data()

# Title
st.title("🔍 Roche AI PoC: NLP Insights from Planner Comments")

# Filters
st.sidebar.header("Filters")
selected_vendor = st.sidebar.selectbox("Select Vendor:", ["All"] + df["VENDOR_NAME"].unique().tolist())
selected_material = st.sidebar.selectbox("Select Material:", ["All"] + df["MATERIAL_NUMBER"].unique().tolist())
selected_root_cause = st.sidebar.selectbox("Select Root Cause:", ["All"] + df["Root_Cause"].unique().tolist())

# Filter data
filtered_df = df.copy()
if selected_vendor != "All":
    filtered_df = filtered_df[filtered_df["VENDOR_NAME"] == selected_vendor]
if selected_material != "All":
    filtered_df = filtered_df[filtered_df["MATERIAL_NUMBER"] == selected_material]
if selected_root_cause != "All":
    filtered_df = filtered_df[filtered_df["Root_Cause"] == selected_root_cause]

# Display filtered comments
st.subheader("Filtered Comments")
st.dataframe(filtered_df[["Comment", "Root_Cause", "VENDOR_NAME", "MATERIAL_NUMBER"]])
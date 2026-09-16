import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

# Set page config
st.set_page_config(page_title="Roche AI PoC - Root Cause Analysis", layout="wide")

# Title
st.title("🔍 Roche AI PoC: Root Cause Analysis Dashboard")
st.markdown("""
This dashboard demonstrates the **automatic extraction of root causes** from planner comments in Roche's ION Material Availability tool.
""")

# Get the absolute path to the project directory
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(project_dir, "outputs", "root_cause_results.csv")


# Load data with caching
@st.cache_data
def load_data():
    df = pd.read_csv(data_path)
    return df


df = load_data()

# Display raw data
st.header("📊 Raw Data")
st.dataframe(df)

# Filter by root cause
st.header("🔍 Filter by Root Cause")
selected_cause = st.selectbox(
    "Select a root cause:", ["All"] + list(df["Root_Cause"].unique())
)
if selected_cause != "All":
    df_filtered = df[df["Root_Cause"] == selected_cause]
else:
    df_filtered = df


# Filter by material
st.header("🔍 Filter by Material")
selected_material = st.selectbox(
    "Select a material:", ["All"] + list(df["Material_ID"].unique())
)
if selected_material != "All":
    df_filtered = df_filtered[df_filtered["Material_ID"] == selected_material]

st.dataframe(df_filtered)


# Visualizations
st.header("📈 Visualizations")

# Histogram
st.subheader("Root Cause Distribution")
root_cause_counts = df_filtered["Root_Cause"].value_counts()
fig, ax = plt.subplots()
root_cause_counts.plot(kind="bar", ax=ax, color="skyblue")
ax.set_title("Root Cause Distribution")
ax.set_xlabel("Root Cause")
ax.set_ylabel("Number of Comments")
st.pyplot(fig)

# Word cloud
st.subheader("Word Cloud of Comments")
text = " ".join(comment for comment in df_filtered["Comment"])
wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
fig, ax = plt.subplots()
ax.imshow(wordcloud, interpolation="bilinear")
ax.axis("off")
st.pyplot(fig)

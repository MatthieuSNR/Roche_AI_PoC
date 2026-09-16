import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

# Get the absolute path to the project directory
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_path = os.path.join(project_dir, "outputs", "root_cause_results.csv")
output_dir = os.path.join(project_dir, "outputs", "visualizations")

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Load results
df = pd.read_csv(input_path)

# 1. Histogram of root causes
root_cause_counts = df["Root_Cause"].value_counts()
plt.figure(figsize=(10, 6))
root_cause_counts.plot(kind="bar", color="skyblue")
plt.title("Root Cause Distribution")
plt.xlabel("Root Cause")
plt.ylabel("Number of Comments")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "root_cause_histogram.png"))  # Save the plot
plt.show()

# 2. Word cloud of comments
text = " ".join(comment for comment in df["Comment"])
wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
plt.figure(figsize=(10, 6))
plt.imshow(wordcloud, interpolation="bilinear")
plt.axis("off")
plt.title("Word Cloud of Comments")
plt.savefig(os.path.join(output_dir, "wordcloud.png"))  # Save the plot
plt.show()

# 3. Histogram of comments by planner
planner_counts = df["Planner_ID"].value_counts()
plt.figure(figsize=(10, 6))
planner_counts.plot(kind="bar", color="lightgreen")
plt.title("Comments by Planner")
plt.xlabel("Planner")
plt.ylabel("Number of Comments")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("../outputs/visualizations/planner_histogram.png")
plt.show()

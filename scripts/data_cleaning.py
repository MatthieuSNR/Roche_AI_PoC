import pandas as pd
import os

# Get the absolute path to the project directory
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(project_dir, "data", "synthetic_data.csv")

# Load the CSV
df = pd.read_csv(data_path)

# Display the first 5 rows to verify
print("=== Raw Data ===")
print(df.head())

# Data cleaning
# 1. Remove duplicates
df = df.drop_duplicates()

# 2. Check for missing values
print("\n=== Missing Values ===")
print(df.isnull().sum())

# 3. Convert Timestamp column to datetime
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# 4. Extract date and time (optional)
df["Date"] = df["Timestamp"].dt.date
df["Time"] = df["Timestamp"].dt.time

# 5. Save cleaned data
output_path = os.path.join(project_dir, "data", "cleaned_data.csv")
df.to_csv(output_path, index=False)

print("\n=== Cleaned Data ===")
print(df.head())

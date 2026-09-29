# Project Steps: NLP Analysis of Roche’s Planner Comments

## 📌 Step 1: Data Loading and Cleaning
- **Objective**: Combine all CSV files from `Snapshot_2026` and clean comments.
- **Actions**:
  - Load all CSV files using `glob` and `pandas`.
  - Remove rows with missing comments (`dropna`).
  - Remove duplicate comments (`drop_duplicates`).
  - Clean comments: Remove prefix `"pseudo, YYYY-MM-DD: "` using `str.split()`.
- **Tools**: `pandas`, `glob`.
- **Output**: `data/cleaned_comments.csv` (all useful columns retained).

## 📌 Step 2: Streamlit Dashboard
- **Objective**: Create an interactive dashboard to filter and display comments.
- **Actions**:
  - Load cleaned data (`cleaned_comments.csv`).
  - Add filters for **vendor, material, root cause**.
  - Display filtered comments in a table.
- **Tools**: `streamlit`, `pandas`.
- **Output**: `scripts/app.py` (basic dashboard).

## 📌 Next Steps
- [ ] Deepen NLP analysis (keyword extraction, root cause correlations).
- [ ] Add visualizations (word clouds, heatmaps).
- [ ] Improve data cleaning for edge cases.





## 🛠️ Scripts
   Script                     | Purpose                          |
 |----------------------------|----------------------------------|
 | `app.py`                   | Streamlit dashboard for predictions. |
 | `data_cleaning.ipynb`      | Data cleaning script             |
 | `nlp_analysis.ipynb`       | NLP analysis Notebook            |

## 📁 Data Structure => to be adapted
 | Field          | Description                          | Example                     |
 |----------------|--------------------------------------|-----------------------------|
 | Timestamp      | Date of the snapshot.                | `2026-09-01`               |
 | Planner_ID     | ID of the planner.                   | `Planner_1`                 |
 | Material_ID    | ID of the material.                  | `MAT_100`                  |
 | Supplier       | Supplier name.                       | `Supplier_X`                |
 | Category       | Current risk category.               | `Potential Stock Out`      |
 | Root_Cause     | Standardized root cause (1 of 38).    | `Supplier Delay`           |
 | Comment        | Free-text comment (EN/DE).           | `"Urgent: delay for MAT_100"` |
# Project Steps: Roche AI PoC - Predictive Analytics for Stock Out Risk

## 🎯 Overview
This project aims to **predict future Stock Out risks** for Roche’s **ION Material Availability Dashboard** using:
- **Historical data** (Timestamp, Material_ID, Supplier, Category, Root_Cause, Comment).
- **Supervised Machine Learning** (RandomForest/XGBoost) to predict the **next category** (e.g., "Stock Out").
- **NLP** (TF-IDF) to extract insights from **English/German comments**.

## 📊 Data Flow
1. **Input**: Historical CSV data (weekly snapshots).
2. **Preprocessing**:
   - Clean comments (remove special characters, lowercase).
   - Encode categorical fields (Supplier, Material_ID, Category).
   - Vectorize comments with TF-IDF.
3. **Feature Engineering**:
   - Add temporal features (e.g., weeks in "Below Safety").
   - Merge with historical patterns (e.g., Supplier X delays).
4. **Model Training**:
   - **Target**: Predict if the **next category** is "Stock Out" (1) or not (0).
   - **Model**: RandomForestClassifier (or XGBoost).
5. **Output**:
   - Probability of Stock Out for a given material.
   - Interactive dashboard (Streamlit) for planners.

## 🛠️ Scripts
   Script                     | Purpose                          |
 |----------------------------|----------------------------------|
 | `predictive_model.py`      | Train the predictive model.      |
 | `app.py`                   | Streamlit dashboard for predictions. |
 | `synthetic_data.csv`      | Synthetic data for testing.      |

## 📁 Data Structure
 | Field          | Description                          | Example                     |
 |----------------|--------------------------------------|-----------------------------|
 | Timestamp      | Date of the snapshot.                | `2026-09-01`               |
 | Planner_ID     | ID of the planner.                   | `Planner_1`                 |
 | Material_ID    | ID of the material.                  | `MAT_100`                  |
 | Supplier       | Supplier name.                       | `Supplier_X`                |
 | Category       | Current risk category.               | `Potential Stock Out`      |
 | Root_Cause     | Standardized root cause (1 of 38).    | `Supplier Delay`           |
 | Comment        | Free-text comment (EN/DE).           | `"Urgent: delay for MAT_100"` |
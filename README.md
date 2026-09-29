# Roche AI PoC: NLP Insights from Planner Comments

## 🎯 Project Overview
This project aims to **extract actionable insights** for Roche’s planner comments using **Natural Language Processing (NLP)**. The goal is to:
- **Quantify recurring issues** (e.g., "50% of delays for Supplier X are due to capacity issues").
- **Identify patterns** in comments (e.g., "urgent" + "Supplier Y" often leads to Stock Out).
- **Provide filters** in a Streamlit dashboard to analyze comments by **supplier, material, or root cause**.

## 📊 Current Status
- **Data Cleaning**: All comments from `Snapshot_2026` are cleaned and stored in `data/cleaned_comments.csv`.
- **Streamlit Dashboard**: A basic dashboard (`scripts/app.py`) displays comments with filters for **vendor, material, and root cause**.
- **Next Steps**: Deepen NLP analysis (keyword extraction, root cause correlations).

## 🛠️ Tools & Libraries
   Tool/Library   | Version   | Purpose                          |
 |----------------|-----------|----------------------------------|
 | Python         | 3.12.4    | Primary scripting language       |
 | pandas         | 2.2.3     | Data manipulation                |
 | spaCy          | 3.8.16    | NLP (text preprocessing)         |
 | Streamlit      | 1.32.0    | Interactive dashboard            |
 | matplotlib     | 3.7.2     | Visualizations                   |
 | seaborn        | 0.12.2    | Statistical plots                |

*(See [docs/tools_justification.md](docs/tools_justification.md) for detailed justifications.)*

## 📁 Project Structure

```
Roche_AI_PoC/
├── data/
│   ├── Snapshot_2026/           # Raw data (not pushed to GitHub)
│   └── cleaned_comments.csv     # Cleaned data for analysis
│
├── docs/
│   ├── project_steps.md         # Step-by-step methodology
│   └── tools_justification.md   # Tools/libraries justification
│
├── outputs/                     # Generated outputs (models, visualizations)
│
├── scripts/
│   ├── app.py                   # Streamlit dashboard
│   ├── nlp_analysis.ipynb       # NLP analysis Notebook
│   ├── data_cleaning.py         # Data cleaning script
│   └──                   
│
└── README.md
```

## 🚀 How to Run
1. **Set up the environment**:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   python -m spacy download de_core_news_sm

2. **Launch the Streamlit dashboard**:
    ```bash
    streamlit run scripts/app.py












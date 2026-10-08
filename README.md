# Roche AI PoC: NLP Insights from Planner Comments

## 🎯 Project Overview
This project aims to **extract actionable insights** for Roche’s planner comments using **Natural Language Processing (NLP)**. The goal is to:
- **Quantify recurring issues** (e.g., "50% of delays for Supplier X are due to capacity issues").
- **Identify patterns** in comments (e.g., "urgent" + "Supplier Y" often leads to Stock Out).
- **Provide filters** in a Streamlit dashboard to analyze comments by **supplier, material, or root cause**.

## 📊 Current Status
- **Data Cleaning**: the comments of the 174 daily snapshots of `Snapshot_2026` are stored in `data/cleaned_comments.csv`: one row per (material, vendor, comment), with `First_Seen`, `Last_Seen`, `N_Snapshots` and `Days_Active` (how long the comment stayed visible).
- **Translation**: German comments are translated to English with DeepL (`Comment_EN`). Every translation is cached in `data/interim/translation_cache.csv`, so a comment is paid for only once.
- **Streamlit Dashboard** (`scripts/app.py`): filters for **vendor, MRP controller, material, root cause and period**; comment-centred statistics ("X% of this vendor's comments are about root cause Y, vs Z% overall", "which vendors / MRP controllers a root cause comes from", how long comments stay open); local LLM summary (LM Studio).
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
│   ├── Snapshot_2026/           # Raw daily snapshots (not pushed to GitHub)
│   ├── interim/                 # translation_cache.csv (not pushed to GitHub)
│   └── cleaned_comments.csv     # Cleaned + translated comments (not pushed to GitHub)
│
├── docs/
│   ├── project_steps.md         # Step-by-step methodology
│   └── tools_justification.md   # Tools/libraries justification
│
├── outputs/                     # Generated outputs (models, visualizations)
│
├── scripts/
│   ├── app.py                   # Streamlit dashboard
│   ├── data_cleaning.py         # Builds data/cleaned_comments.csv from the snapshots
│   ├── translation.py           # Language detection + DeepL translation (Comment_EN)
│   ├── stats_engine.py          # All statistics (pandas), used by the dashboard and the LLM
│   ├── llm_summary.py           # AI summary with a local LLM (LM Studio)
│   ├── config.py                # Reads the DeepL key from .env
│   └── *.ipynb                  # Exploration notebooks
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

   cp .env.example .env    # then fill DEEPL_API_KEY
   ```

2. **Build and translate the comments** (after adding new snapshots to `data/Snapshot_2026/`):
   ```bash
   python scripts/data_cleaning.py
   python scripts/translation.py --dry-run   # how many characters will be sent to DeepL
   python scripts/translation.py
   ```

3. **Launch the Streamlit dashboard**:
   ```bash
   streamlit run scripts/app.py
   ```













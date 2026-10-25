## 📁 Project Structure

The project is organized as follows to ensure **clarity, reproducibility, and maintainability** (state on 16 October 2026; this file was a projection at the start of the project and now describes the real tree).

```
Roche_AI_PoC/
├── data/                        # Confidential: never pushed to GitHub
│   ├── Snapshot_2026/           # Raw daily snapshots (26 CSV files, 174 days)
│   ├── interim/                 # translation_cache.csv, saved_views.json, backups
│   └── cleaned_comments.csv     # Cleaned + translated comments (one row per material, vendor, comment)
│
├── scripts/                     # Python scripts of the PoC
│   ├── app.py                   # Streamlit dashboard (one scrolling page, 7 sections, password page)
│   ├── ui.py                    # Layout: ION-like look, top menu, loading screen, result card
│   ├── stats_engine.py          # All statistics (pandas), used by the dashboard and the LLM
│   ├── data_cleaning.py         # Builds data/cleaned_comments.csv: journal entries split, signatures removed, abbreviations written out
│   ├── abbreviations.py         # Reads the library, writes abbreviations out, review sheet for the planners
│   ├── translation.py           # Language detection + DeepL translation (Comment_EN)
│   ├── pseudonymise.py          # Hides names/IDs before text goes to DeepL or the Mistral API
│   ├── llm_summary.py           # Smart Analysis: Mistral API (cloud) or LM Studio (local backup)
│   ├── nlp_pipeline.py          # Text preprocessing (spaCy) for the NLP exploration
│   ├── config.py                # Reads the keys from .env
│   └── *.ipynb                  # Notebooks to test the scripts (cleaning, translation, NLP, LLM)
│
├── lexicon/
│   └── abbreviations.csv        # Library of abbreviations (DE/EN), proposed meanings, validated by the planners; no real comment in it
├── tests/                       # pytest: journal entries, abbreviations, pseudonymisation, cloud summary (no Roche data, no network)
├── assets/                      # Roche logo and favicon
├── .streamlit/config.toml       # Theme close to the ION Material Availability dashboard
├── outputs/                     # Generated outputs (visualizations, models)
├── docs/                        # Project documentation
│   ├── tools_justification.md   # Justification of every tool and library
│   ├── projected_project_structure.md   # This file
│   └── project_steps.md         # Methodology and data update procedure
│
├── share.sh                     # Shares the dashboard through an ngrok tunnel (usability tests)
├── venv/                        # Virtual environment (not pushed)
├── .env                         # API keys and app password (not pushed); template: .env.example
├── requirements.txt             # Python dependencies list
└── README.md                    # Project overview and instructions
```

### **Key Notes:**
- **Data flow**: `Snapshot_2026/` → `data_cleaning.py` (entries split, signatures removed, `abbreviations.py` + `lexicon/abbreviations.csv`) → `cleaned_comments.csv` → `translation.py` (with `pseudonymise.py`, entry by entry) → `Comment_EN` → `stats_engine.py` → `app.py` → `llm_summary.py` (Smart Analysis).
- **`stats_engine.py` is the single source of figures**: the dashboard displays them and the LLM only receives them, so the LLM never computes anything.
- **`data/`, `.env`, `venv/`**: confidential or machine-specific, excluded by `.gitignore`. Only code and documentation are pushed.
- **`scripts/` is flat on purpose**: a modular `src/` layout was tried and set aside (history of the repository); the notebooks test the same scripts instead of duplicating code.
- **`tests/`**: use synthetic data only; the API clients are replaced by fakes.

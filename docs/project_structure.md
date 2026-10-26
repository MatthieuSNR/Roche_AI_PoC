## 📁 Project Structure

State on 26 October 2026. Every file listed here is used; files that no longer served the pipeline (an early spaCy
root-cause matcher in French, its visualisation script, an empty NLP notebook) were removed on that date and remain
in the Git history.

```
Roche_AI_PoC/
├── data/                          # Confidential: never pushed to GitHub (.gitignore)
│   ├── Snapshot_2026/             # Raw daily snapshots: 26 CSV files (W14 to W38), 174 days
│   ├── interim/                   # Files generated or kept on this Mac
│   │   ├── translation_cache.csv          # Every DeepL translation already paid for (+ glossary version)
│   │   ├── cleaned_comments_before_rebuild.csv  # Older build, its Comment_EN feeds the cache
│   │   ├── deepl_glossary.json            # Id and hash of the glossary created on DeepL
│   │   ├── abbreviations_for_review.xlsx  # Sheet for the planners: abbreviation, meaning, language
│   │   ├── abbreviation_evidence.csv      # Real excerpts that justify the proposed meanings (read by --report)
│   │   └── saved_views.json               # Saved views of the dashboard
│   ├── cleaned_comments.csv       # One row per (material, vendor, comment): cleaned, expanded, translated
│   └── item_tracking.csv          # One row per (day, material, vendor) from ALL snapshot rows (Insights Lab)
│
├── lexicon/                       # Versioned reference tables, no real comment in them
│   ├── abbreviations.csv          # Library of abbreviations (DE / EN), proposed meanings, to be validated by the planners
│   └── glossary_de_en.csv         # DeepL glossary of the German supply-chain jargon
│
├── scripts/                       # Python code of the PoC (flat: the notebooks import the modules directly)
│   │   # --- Pipeline (data/Snapshot_2026 -> data/cleaned_comments.csv)
│   ├── data_cleaning.py           # Steps 1-6: merge, commented rows, journal entries, one row per comment, language, abbreviations; save with Comment_EN from the cache
│   ├── entries.py                 # Separator " ¦▸ " between the journal entries of a cell (used by every module)
│   ├── abbreviations.py           # Reads lexicon/abbreviations.csv, writes abbreviations out, Excel sheet for the planners
│   ├── translation.py             # Step 7: language per entry, DeepL with cache and glossary -> Comment_EN
│   ├── glossary.py                # Reads lexicon/glossary_de_en.csv, creates / reuses the DeepL glossary
│   ├── pseudonymise.py            # Hides names and IDs before text goes to DeepL or to the Mistral API
│   │   # --- Dashboard
│   ├── app.py                     # Streamlit dashboard (one scrolling page, password page when shared)
│   ├── ui.py                      # Layout: ION-like look, top menu, loading screen, result card
│   ├── stats_engine.py            # All statistics (pandas), used by the dashboard and the LLM
│   │   # --- Insights Lab (new pages, second row of the menu, to validate)
│   ├── tracking.py                # Builds data/item_tracking.csv from all snapshot rows
│   ├── insights.py                # Grouping of similar comments, trends, root cause x impact, weak signals
│   ├── insights_pages.py          # The four new pages (Streamlit)
│   ├── llm_summary.py             # Smart Analysis: Mistral API (cloud) or LM Studio (local backup)
│   ├── config.py                  # Reads the keys from .env
│   │   # --- Notebooks: run each step and check its result
│   ├── data_cleaning.ipynb        # Steps 1-6, one cell per step, + explorations A-C (tokens, keywords, heatmap)
│   ├── translation.ipynb          # Step 7 (7.1-7.5)
│   └── llm_summary.ipynb          # Statistics, prompt, pseudonymised prompt, cloud / local analysis
│
├── tests/                         # pytest, synthetic data only, no network
│   ├── test_comment_cleaning.py   # Journal entries, signatures, snapshot merge, abbreviations, entry-by-entry translation
│   ├── test_glossary.py           # DeepL glossary: validation, hash, refresh of stale translations
│   ├── test_pseudonymise.py       # Placeholders replaced and restored (DeepL path)
│   ├── test_cloud_summary.py      # No real name in the Mistral request, aliases restored in the answer
│   └── test_insights.py           # Grouping rules, tracking table, status change, root cause x impact, weak signals
│
├── docs/
│   ├── project_steps.md           # Methodology, step by step, and data update procedure
│   ├── project_structure.md       # This file
│   └── tools_justification.md     # Justification of every tool and library
│
├── assets/                        # Roche logo and favicon
├── .streamlit/config.toml         # Theme close to the ION Material Availability dashboard
├── outputs/                       # Local outputs, not pushed (demo teaser)
├── share.sh                       # Shares the dashboard through an ngrok tunnel (usability tests)
├── requirements.txt               # Python dependencies
├── .env / .env.example            # API keys and app password (.env never pushed)
└── README.md                      # Overview and how to run
```

### **Key Notes:**
- **Data flow**: `Snapshot_2026/` → `data_cleaning.py` (steps 1-6, with `entries.py`, `abbreviations.py` + `lexicon/abbreviations.csv`) → `cleaned_comments.csv` → `translation.py` (step 7, with `pseudonymise.py`, `glossary.py`, the cache) → `Comment_EN` → `stats_engine.py` → `app.py` → `llm_summary.py` (Smart Analysis).
- **One function per cleaning step**, one notebook cell per step: the result of every step can be checked on its own. The notebooks call the functions of the scripts, they do not duplicate code.
- **Insights Lab**: `Snapshot_2026/` → `tracking.py` → `item_tracking.csv` → `insights.py` → `insights_pages.py`, drawn by `app.py` when the URL has `?page=...`. The main page stays unchanged until a new page is validated.
- **`stats_engine.py` is the single source of figures**: the dashboard displays them and the LLM only receives them, so the LLM never computes anything.
- **`lexicon/` vs `data/interim/`**: `lexicon/` holds the reference tables, versioned and free of real comments; `data/interim/` holds files generated from the confidential data, never pushed.
- **`scripts/` is flat on purpose**: a modular `src/` package was tried and set aside (history of the repository); a flat folder lets the notebooks import the modules without installation.
- **`data/`, `.env`, `venv/`, `outputs/`**: confidential or machine-specific, excluded by `.gitignore`. Only code and documentation are pushed. Notebooks are pushed **without outputs** (their outputs show real comments).

# Project Steps: NLP Analysis of Roche’s Planner Comments

## 📌 Step 1: Data Loading and Cleaning
- **Objective**: Combine all daily snapshot CSV files from `Snapshot_2026` and clean the comments.
- **Actions** (`scripts/data_cleaning.py`):
  - Load all CSV files using `glob` and `pandas`, keep only the rows with a comment.
  - Clean comments: remove the prefix `"pseudo, YYYY-MM-DD: "` (regex; comments without prefix are kept).
  - Keep one row per (material, vendor, comment) instead of one row per distinct text, so that
    "X% of this vendor's comments" counts every vendor concerned.
  - Record how long each comment stayed in the dashboard: `First_Seen`, `Last_Seen`,
    `N_Snapshots`, `Days_Active`. The other columns (status, root cause, impact) take their latest known value.
- **Tools**: `pandas`, `glob`, `re`.
- **Output**: `data/cleaned_comments.csv` (all useful columns retained).

## 📌 Step 1b: Language Detection and Translation
- **Objective**: Analyse all comments in English.
- **Actions** (`scripts/translation.py`):
  - Detect the language, restricted to English / German (`langdetect` + a small German lexicon).
  - Translate German comments to English with DeepL → column `Comment_EN`.
  - Cache every translation in `data/interim/translation_cache.csv`: a comment is paid for only once.
- **Tools**: `langdetect`, `deepl`.
- **Output**: `comment_language` and `Comment_EN` columns in `data/cleaned_comments.csv`.

## 📌 Step 2: Streamlit Dashboard
- **Objective**: Create an interactive dashboard to filter and display comments.
- **Actions**:
  - Load cleaned data (`cleaned_comments.csv`).
  - Add filters for **vendor, MRP controller, material, root cause and period**.
  - Display filtered comments in a table.
  - Comment-centred statistics (`scripts/stats_engine.py`): share of the selection vs all comments,
    root causes per vendor / MRP controller, where a root cause comes from, how long comments stay open.
- **Tools**: `streamlit`, `pandas`, `matplotlib`.
- **Output**: `scripts/app.py` (one scrolling page: overview + 7 sections, top menu to jump between them; layout in `scripts/ui.py`).

## 🔄 Updating the Data (new snapshots)
Run everything from the project root, with the virtual environment active:
```bash
cd /Users/matthieusanner/Roche_AI_PoC
source venv/bin/activate
```

| Step | Command | What it does |
|------|---------|--------------|
| 1. Add the files | copy the new CSV files into `data/Snapshot_2026/` | Same columns as the existing files; the file name does not matter, days already present are not counted twice. |
| 2. Rebuild | `python scripts/data_cleaning.py` | Re-reads **all** snapshots and rewrites `data/cleaned_comments.csv` (~15 s): new comments added, `Last_Seen` / `Days_Active` updated, latest root cause and impact taken. |
| 3. Translate | `python scripts/translation.py --dry-run` then `python scripts/translation.py` | The dry run only counts the characters to send. The real run translates **only the new** German comments (the others come from the cache) and prints the monthly DeepL usage. If interrupted, just run it again. |
| 4. Reload | Streamlit → menu **⋮** → **Clear cache**, then **Rerun** (or `Ctrl + C` and `streamlit run scripts/app.py`) | Streamlit keeps the data in memory: "Rerun" alone does not reload the CSV. |

- ⚠️ Always run step 3 right after step 2: the rebuilt file has no `Comment_EN` column until the translation is done, and the dashboard needs it.
- **GitHub**: a data update needs no push. Snapshots, `cleaned_comments.csv` and the translation cache are confidential and excluded by `.gitignore`. Only code changes (`scripts/`) are pushed.
- **New DeepL key**: put it in the `.env` file at the project root (`DEEPL_API_KEY=...`); `scripts/config.py` reads it from there.

## 📌 Next Steps
- [ ] Deepen NLP analysis (keyword extraction, root cause correlations).
- [ ] Add visualizations (word clouds, heatmaps).
- [x] Improve data cleaning for edge cases (comments without prefix, one row per material and vendor).





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
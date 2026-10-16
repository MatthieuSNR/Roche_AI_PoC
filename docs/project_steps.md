# Project Steps: NLP Analysis of Roche’s Planner Comments

Status on 16 October 2026. Each step names the script that implements it.

## 📌 Step 1: Data Loading and Cleaning
- **Objective**: Combine all daily snapshot CSV files from `Snapshot_2026` and clean the comments.
- **Actions** (`scripts/data_cleaning.py`):
  - Load all CSV files using `glob` and `pandas` (26 files, 174 daily snapshots, ≈2.07 million rows), keep only the rows with a comment (≈87,700).
  - Clean comments: remove the prefix `"pseudo, YYYY-MM-DD: "` (regex; comments without prefix are kept).
  - Keep one row per (material, vendor, comment) instead of one row per distinct text, so that
    "X% of this vendor's comments" counts every vendor concerned (result: ≈2,265 rows).
  - Record how long each comment stayed in the dashboard: `First_Seen`, `Last_Seen`,
    `N_Snapshots`, `Days_Active`. The other columns (status, root cause, impact) take their latest known value.
- **Tools**: `pandas`, `glob`, `re`.
- **Output**: `data/cleaned_comments.csv` (all useful columns retained).

## 📌 Step 1b: Language Detection and Translation
- **Objective**: Analyse all comments in English (about two thirds are written in German).
- **Actions** (`scripts/translation.py`):
  - Detect the language, restricted to English / German (`langdetect` + a small German lexicon).
  - **Pseudonymise** each German comment before it is sent (Step 3), translate it with DeepL, restore the original values locally → column `Comment_EN`.
  - Cache every translation in `data/interim/translation_cache.csv`: a comment is paid for only once.
- **Tools**: `langdetect`, `deepl`.
- **Output**: `comment_language` and `Comment_EN` columns in `data/cleaned_comments.csv`.

## 📌 Step 2: Streamlit Dashboard
- **Objective**: An interactive dashboard that shows at a glance where the issues are, for any selection (vendor, MRP controller, material...).
- **Actions** (`scripts/app.py`, layout in `scripts/ui.py`):
  - Load cleaned data (`cleaned_comments.csv`, cached with `st.cache_data`).
  - Sidebar filters in this order: **MRP controller, purchasing group, vendor, material, root cause, impact**, plus the period. Every filter is a **multiselect** (empty = All) and the filters **cascade** (each one only offers the values left by the filters above it).
  - **Saved views**: filters, period and table columns saved under a name and re-applied in one click (`data/interim/saved_views.json`, local, not pushed).
  - Comments table with a **▥ Columns** panel (show/hide, drag and drop order).
  - Comment-centred statistics (`scripts/stats_engine.py`): share of the selection vs all comments, root causes per vendor / MRP controller, where a root cause comes from, how long comments stay open, weekly trends; **Top 5 / 10 / 20** views.
  - **Smart Analysis**: written review of the selection (Step 4).
- **Tools**: `streamlit`, `streamlit-sortables`, `pandas`, `matplotlib`.
- **Output**: one scrolling page (overview with the ION-style material status tiles + 7 sections, top menu to jump between them).

## 📌 Step 3: Pseudonymisation (data governance)
- **Objective**: Reduce what leaves the machine whenever text is sent to a cloud service.
- **Actions** (`scripts/pseudonymise.py`, tests in `tests/`):
  - **DeepL**: comments only; e-mails, @-mentions, supplier names, material numbers, long numbers and the company name are replaced by placeholders (`<keep>` tags) and restored after translation.
  - **Mistral API**: the prompt of the Smart Analysis is pseudonymised by `PromptPseudonymiser` (`VENDOR_n`, `MRP_n`, `PGROUP_n`, `MATERIAL_n`, plus the elements above in the comments). The alias → name table stays in memory; aliases in the answer are replaced by the real names before display.
  - Prices and volumes are never part of the prompt (only shares, counts, trends and a few comments).
- **Limits** (thesis 3.8): abbreviated or misspelled supplier names and person names without "@" are not detected; MRP controllers and purchasing groups are replaced in the statistics, not inside free text. Pseudonymisation reduces the risk; it does not replace Roche's approval.

## 📌 Step 4: Smart Analysis (LLM)
- **Objective**: A short written analysis of the current selection, from figures that pandas has already computed.
- **Actions** (`scripts/llm_summary.py`):
  - Compact prompt: key statistics (every key states its unit) + the most frequent informative comments of the three main root causes.
  - Five fixed sections: Key findings, Trend over time, Where the issues come from, Risks to escalate, Recommended actions; the answer is streamed.
  - **Cloud** (shown in the dashboard): Mistral API, default model `ministral-14b-latest` (`MISTRAL_MODEL` in `.env`), pseudonymised prompt. Chosen on 16 Oct. so that the app can run on any laptop and be deployed, and the Mac no longer heats up.
  - **Local** (backup, `render_ai_summary("local")`): LM Studio with Mistral 7B Instruct v0.3; no data leaves the machine.
- **Tools**: `openai` client (OpenAI-compatible APIs), Mistral API, LM Studio.
- **Output**: the *Smart Analysis* section of the dashboard.

## 📌 Step 5: Remote Access for Usability Tests
- **Objective**: Let planners test the dashboard in their own browser with the real data.
- **Actions**: `./share.sh` starts Streamlit and an ngrok tunnel; the app asks for `APP_PASSWORD` (set in `.env`). The data stays on this Mac; the dashboard is reachable only while the script runs.
- **Limits**: one shared password, link changes at each start, third party (ngrok) in the path: acceptable for a short test, not for production. Details in `tools_justification.md`, section 12.

## 📌 Step 6: Tests
- **Actions**: `python -m pytest -q tests` — pseudonymisation (identifying elements replaced and restored) and the cloud summary (no real name in the prompt, aliases restored in the streamed answer), with a fake API client: no network, no key, no Roche data.

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
| 3. Translate | `python scripts/translation.py --dry-run` then `python scripts/translation.py` | The dry run only counts the characters to send. The real run pseudonymises and translates **only the new** German comments (the others come from the cache) and prints the monthly DeepL usage. If interrupted, just run it again. |
| 4. Reload | Streamlit → menu **⋮** → **Clear cache**, then **Rerun** (or `Ctrl + C` and `streamlit run scripts/app.py`) | Streamlit keeps the data in memory: "Rerun" alone does not reload the CSV. |

- ⚠️ Always run step 3 right after step 2: the rebuilt file has no `Comment_EN` column until the translation is done, and the dashboard needs it.
- **GitHub**: a data update needs no push. Snapshots, `cleaned_comments.csv`, the translation cache and the saved views are confidential and excluded by `.gitignore`. Only code changes (`scripts/`) are pushed.
- **Keys**: `DEEPL_API_KEY`, `MISTRAL_API_KEY` and `APP_PASSWORD` go in the `.env` file at the project root; `scripts/config.py` reads it. Never commit it.

## 📌 Next Steps
- [x] Improve data cleaning for edge cases (comments without prefix, one row per material and vendor).
- [x] Comment-centred statistics, filters and saved views in the dashboard.
- [x] Pseudonymisation before DeepL and before the Mistral API.
- [x] Smart Analysis with a cloud model; local model kept as backup.
- [ ] Validate with Roche (tool engineer / IT) the use of an external LLM API and the hosting of a demo outside Roche.
- [ ] Check Mistral's data retention and training terms for the plan used, and cite them in the thesis.
- [ ] Revoke the DeepL key that was once pushed to GitHub (it remains in the Git history).
- [ ] Evaluate the Smart Analysis (are the figures and quotes faithful? compare cloud vs local on the same selections); no formal evaluation exists yet.
- [ ] Deepen NLP analysis (keyword extraction, root cause correlations); add word clouds / heatmaps.
- [ ] If Roche adopts the dashboard: rebuild it on an internal platform (e.g., R Shiny, Posit Connect).

# Project Steps: NLP Analysis of Roche’s Planner Comments

Status on 16 October 2026. Each step names the script that implements it.

## 📌 Step 1: Data Loading and Cleaning
- **Objective**: Combine all daily snapshot CSV files from `Snapshot_2026` and clean the comments.
- **Actions** (`scripts/data_cleaning.py`):
  - Load all CSV files using `glob` and `pandas` (26 files, 174 daily snapshots, ≈2.07 million rows), keep only the rows with a comment (≈87,700).
  - **Cleaning in six checkable steps** (one function each in `data_cleaning.py`, one cell each in `data_cleaning.ipynb`, so that the result of every step can be inspected): 1. `merge_snapshots` (assemble the weekly CSV files), 2. `keep_commented_rows`, 3. `split_journal`, 4. `deduplicate_comments`, 5. `detect_languages`, 6. `expand_abbreviations`; then, in `translation.py`, 7. pseudonymise and DeepL. The language is detected before the abbreviations are written out because the same abbreviation can have another meaning in English and in German. Rows with a root cause or an impact but no comment (2,234 and 1,897 of 2,066,102) are not in `cleaned_comments.csv`; a separate tracking table for the trends over time is planned.
  - **Split the journal**: a comment cell holds several entries, each signed and dated (`login, 2026-06-18: message`), and the tool re-signs an entry every time it is edited (chains such as `a, 2026-07-16: a, 2026-07-13: b, 2026-06-26: message`). Each entry is cut out on its own (`parse_comment`); typos in the signature (`20206-07-23`, `08072026`, missing colon, a signature in the middle of a line) are tolerated; an unsigned line continues the previous entry.
  - **Remove the metadata**: the whole signature chain (login, date, time) leaves the text. The logins are staff identifiers, i.e. personal data (thesis 3.7): they are not kept; only anonymous metadata remains (`N_Entries`, `N_Authors`, `First_Entry_Date`, `Last_Entry_Date`). The entries stay in the same cell, one after the other, separated by the visible marker ` ¦▸ ` (`scripts/entries.py`; the marker appears nowhere in the raw comments), so that their succession remains visible in Excel, in a text editor and in the dashboard.
  - **Write the abbreviations out** (`scripts/abbreviations.py`, library `lexicon/abbreviations.csv`): `Comment_Expanded` is `Comment` with the certain abbreviations written out, entry by entry and in the language of the entry (`50 Stk.` → `50 Stück`, `KW34` → `Kalenderwoche 34`). `Comment` keeps the original wording. `Entry_Languages` records the language of each entry.
  - Keep one row per (material, vendor, comment) instead of one row per distinct text, so that
    "X% of this vendor's comments" counts every vendor concerned (result: ≈2,265 rows).
  - Record how long each comment stayed in the dashboard: `First_Seen`, `Last_Seen`,
    `N_Snapshots`, `Days_Active`. The other columns (status, root cause, impact) take their latest known value.
- **Tools**: `pandas`, `glob`, `re`.
- **Output**: `data/cleaned_comments.csv` (all useful columns retained, plus `Comment_Expanded`, `Entry_Languages` and the entry metadata).
- **DeepL glossary** (`lexicon/glossary_de_en.csv`, `scripts/glossary.py`): fixes jargon that DeepL translates inconsistently (in the first 1,011 translations `Vorzug` came out as priority, preference or expediting, `Abriss` once as demolition, `Rückbuchung` as refund). Only rows with `use = yes` and `confidence = high` are uploaded; inflected forms are listed separately because DeepL matches the written form, case-sensitively. The glossary is created once on DeepL and reused (id and content hash in `data/interim/deepl_glossary.json`; replaced when the CSV changes). The cache records the glossary version of every translation: `--dry-run` shows how many earlier translations contain a term but were made without it, and `--refresh-glossary` redoes them (extra DeepL characters). Limit: a glossary imposes one translation per term, so ambiguous words (`Freigabe`, `Rückstand`) stay out until the planners decide.
- **Order of the pipeline**: split entries and remove signatures → write abbreviations out → pseudonymise → DeepL (German entries only) → rest unchanged.
- **Library of abbreviations**: one row per abbreviation with a proposed meaning (German and English), context (material planning, production planning, quality, logistics...), confidence and an `expand` flag. Only rows with `expand = yes` (certain meaning, confidence high) are written out; ambiguous ones (e.g. `LT`: delivery date or lead time), unknown ones and names of companies or products stay untouched until the planners have confirmed them. After validation: set `expand` to `yes`, `python scripts/data_cleaning.py`. `python scripts/abbreviations.py --report` writes a review sheet with frequencies and examples (confidential, `data/interim`); `--discover` lists abbreviation-like words not yet in the library.

## 📌 Step 1b: Language Detection and Translation
- **Objective**: Analyse all comments in English (about two thirds are written in German).
- **Actions** (`scripts/translation.py`):
  - Detect the language, restricted to English / German (`langdetect` + a small German lexicon).
  - Work **entry by entry** on `Comment_Expanded`: **pseudonymise** each German entry before it is sent (Step 3), translate it with DeepL, restore the original values locally; the entries are put back separated by ` ¦▸ ` → column `Comment_EN`.
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
  - **DeepL**: comments only; e-mails, @-mentions, names of the sourcing managers, supplier names, material numbers, long numbers and the company name are replaced by placeholders (`<keep>` tags) and restored after translation.
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
- [ ] Have the DeepL glossary (`lexicon/glossary_de_en.csv`) validated by the planners together with the abbreviations: confirm or correct the English term, set `status`, then `python scripts/translation.py --dry-run` and, if the cost is acceptable, `--refresh-glossary`.
- [ ] Have the abbreviation library validated by the planners (Johannes and Alexis): review sheet `data/interim/abbreviations_review.csv`; start with the low-confidence abbreviations, `LT` first.
- [ ] Evaluate the Smart Analysis (are the figures and quotes faithful? compare cloud vs local on the same selections); no formal evaluation exists yet.
- [ ] Deepen NLP analysis (keyword extraction, root cause correlations); add word clouds / heatmaps.
- [ ] If Roche adopts the dashboard: rebuild it on an internal platform (e.g., R Shiny, Posit Connect).

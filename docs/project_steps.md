# Project Steps: NLP Analysis of Roche’s Planner Comments

Status on 26 October 2026. Each part names the script that implements it. Part A builds the comments file in seven
numbered steps; the same numbers are used in the code (`data_cleaning.py`, `translation.py`) and in the notebooks.

## 📌 Part A: Building the Comments File (pipeline steps 1 to 7)
- **Objective**: one clean, anonymous, English table of the planner comments, `data/cleaned_comments.csv`, built from the daily snapshots.
- **Principle**: one function per step, which takes a table and returns a table, and one notebook cell per step that shows the rows before and after and a few "before / after" examples. The result of every step can be checked on its own.

| Step | Function | What happens | Result on 26 Oct. |
|------|----------|--------------|-------------------|
| 1 | `merge_snapshots` | Assemble the weekly snapshot CSV files | 25 files read (1 skipped), 174 days, 2,054,131 rows |
| 2 | `keep_commented_rows` | Keep the rows with a comment | 87,177 rows |
| 3 | `split_journal` | Cut each cell into its journal entries, remove login + date + time | 87,132 rows (45 with only a signature or "n/a") |
| 4 | `deduplicate_comments` | One row per (material, vendor, comment) + how long it stayed visible | 2,231 comments |
| 5 | `detect_languages` | Language (DE / EN) of every entry, on the original wording | 1,717 German and 797 English entries |
| 6 | `expand_abbreviations` | Write the certain abbreviations out, in the language of the entry | 832 comments changed |
| 7 | `add_translations` | Pseudonymise, translate the German entries with DeepL (glossary, cache) | `Comment_EN`; 971 distinct German entries, all cached |

Steps 1 to 6: `scripts/data_cleaning.py` and `data_cleaning.ipynb`; step 7: `scripts/translation.py` and `translation.ipynb`.

**Save** (`save_cleaned_comments`): the file is written with `Comment_EN` already filled from the translation cache (no DeepL call). A rebuild therefore keeps every translation already paid for, and the file is directly usable by the dashboard; only German entries that are not in the cache yet need step 7 (until then they stay in German in `Comment_EN`, and the save step says how many there are).

### Step 1: Assemble the snapshots
- `glob` + `pandas` read every CSV file of `data/Snapshot_2026` (one file per week, one snapshot per day). `Issue` is renamed `Root_Cause`.
- Week 27 exists twice: `W27_Clean.csv` holds only its first day (29.06), `W27_FullClean.csv` the whole week, with identical rows for that day. A `_Clean` file is skipped when the `_FullClean` of the same week exists, otherwise 11,971 rows were counted twice. Check in the notebook: about 12,000 rows per day (min 10,799, max 12,660).

### Step 2: Keep the commented rows
- A row is kept when its comment is neither empty nor only spaces.
- What is lost: 2,218 of the 48,589 rows with a root cause and 1,889 of the 17,908 rows with an impact have no comment. They are not in `cleaned_comments.csv`; a separate tracking table (one row per snapshot with root cause, impact, status, vendor, MRP controller, purchasing group, without comment text) is planned for the trends over time.

### Step 3: Split the journal and remove the signatures
- A comment cell is a **journal**: several entries, each signed and dated (`login, 2026-06-18: message`), and the tool re-signs an entry every time it is edited (chains such as `a, 2026-07-16: a, 2026-07-13: b, 2026-06-26: message`). Each entry is cut out on its own (`parse_comment`); typos in the signature (`20206-07-23`, `08072026`, missing colon, a signature in the middle of a line) are tolerated; an unsigned line continues the previous entry.
- The whole signature chain (login, date, time) leaves the text. The logins are staff identifiers, i.e. personal data (thesis 3.7): they are not kept; only anonymous metadata remains (`N_Entries`, `N_Authors`, `First_Entry_Date`, `Last_Entry_Date`).
- The entries stay in the same cell, one after the other, separated by the visible marker ` ¦▸ ` (`scripts/entries.py`; the marker appears nowhere in the raw comments), so that their succession remains visible in Excel, in a text editor, in `grep` and in the dashboard.
- An entry that says nothing (`n/a`, `-`) is dropped, and so is a row left without any entry (pandas would otherwise read `n/a` back as an empty value).

### Step 4: One row per (material, vendor, comment)
- A comment stays visible for many days: instead of one row per snapshot, one row per (material, vendor, comment), so that "X% of this vendor's comments" counts every vendor concerned.
- How long the comment stayed in the dashboard: `First_Seen`, `Last_Seen`, `N_Snapshots`, `Days_Active`. The other columns (status, root cause, impact...) take their latest known value; the rows are sorted with a stable sort so that this value does not change from one run to the next.

### Step 5: Language of every entry
- `langdetect`, restricted to English / German, with a small German lexicon as fallback (`translation.detect_language`). Result in `Entry_Languages` (`de|en|de`, one language per entry).
- This step comes **before** the abbreviations, on the original wording, because the same abbreviation can mean something else in English and in German.
- Known limit: short mixed entries (`via SafetyStock gedeckt`) can be labelled English.

### Step 6: Write the abbreviations out
- `scripts/abbreviations.py`, library `lexicon/abbreviations.csv`: `Comment_Expanded` is `Comment` with the certain abbreviations written out, entry by entry and in the language of the entry (`50 Stk.` → `50 Stück`, `KW34` → `Kalenderwoche 34`). `Comment` keeps the original wording.
- **Library**: one row per abbreviation with a proposed meaning (German and English), context (material planning, production planning, quality, logistics...), confidence and an `expand` flag. Only rows with `expand = yes` and confidence high are written out; ambiguous ones (e.g. `LT`: delivery date or lead time), unknown ones and names of companies or products stay untouched until the planners have confirmed them. After validation: set `expand` to `yes` and rebuild.
- **Sheet for the planners** (step 6b): `data/interim/abbreviations_for_review.xlsx` (abbreviation, meaning, language), also `python scripts/abbreviations.py --sheet`. `--report` writes, on demand only, a detailed CSV with frequencies, examples and the evidence of each proposed meaning (confidential); `--discover` lists abbreviation-like words not yet in the library.

### Step 7: Translate (`scripts/translation.py`)
- **Objective**: analyse all comments in English (about two thirds contain German).
- Entry by entry, on `Comment_Expanded`, with the languages of step 5: each German entry is **pseudonymised** (Part C), translated with DeepL, and the original values are restored locally; the entries are put back separated by ` ¦▸ ` → `Comment_EN`, plus `comment_language`.
- **Cache**: every translation is stored in `data/interim/translation_cache.csv`; an entry is paid for once, even after a rebuild. `--dry-run` only counts the characters to send.
- **DeepL glossary** (`lexicon/glossary_de_en.csv`, `scripts/glossary.py`): fixes jargon that DeepL translates inconsistently (in the first 1,011 translations `Vorzug` came out as priority, preference or expediting, `Abriss` once as demolition, `Rückbuchung` as refund). Only rows with `use = yes` and `confidence = high` are uploaded; inflected forms are listed separately because DeepL matches the written form, case-sensitively. The glossary is created once on DeepL and reused (id and content hash in `data/interim/deepl_glossary.json`; replaced when the CSV changes). The cache records the glossary version of every translation: `--dry-run` shows how many earlier translations contain a term but were made without it, and `--refresh-glossary` redoes them (extra DeepL characters). Limit: a glossary imposes one translation per term, so ambiguous words (`Freigabe`, `Rückstand`) stay out until the planners decide.
- **Tools**: `pandas`, `glob`, `re`, `langdetect`, `deepl`, `openpyxl` (Excel sheet).
- **Output**: `data/cleaned_comments.csv`: the useful snapshot columns, `Comment`, `Comment_Expanded`, `Comment_EN`, `comment_language`, `Entry_Languages`, the entry metadata and the persistence columns.

## 📌 Part B: Streamlit Dashboard
- **Objective**: An interactive dashboard that shows at a glance where the issues are, for any selection (vendor, MRP controller, material...).
- **Actions** (`scripts/app.py`, layout in `scripts/ui.py`):
  - Load cleaned data (`cleaned_comments.csv`, cached with `st.cache_data`).
  - Sidebar filters in this order: **MRP controller, purchasing group, vendor, material, root cause, impact**, plus the period. Every filter is a **multiselect** (empty = All) and the filters **cascade** (each one only offers the values left by the filters above it).
  - **Saved views**: filters, period and table columns saved under a name and re-applied in one click (`data/interim/saved_views.json`, local, not pushed).
  - Comments table with a **▥ Columns** panel (show/hide, drag and drop order).
  - Comment-centred statistics (`scripts/stats_engine.py`): share of the selection vs all comments, root causes per vendor / MRP controller, where a root cause comes from, how long comments stay open, weekly trends; **Top 5 / 10 / 20** views.
  - **Smart Analysis**: written review of the selection (Part D).
- **Tools**: `streamlit`, `streamlit-sortables`, `pandas`, `matplotlib`.
- **Output**: one scrolling page (overview with the ION-style material status tiles + 7 sections, top menu to jump between them).

## 📌 Part C: Pseudonymisation (data governance)
- **Objective**: Reduce what leaves the machine whenever text is sent to a cloud service.
- **Actions** (`scripts/pseudonymise.py`, tests in `tests/`):
  - **DeepL**: comments only; e-mails, @-mentions, names of the sourcing managers, supplier names, material numbers, long numbers and the company name are replaced by placeholders (`<keep>` tags) and restored after translation.
  - **Mistral API**: the prompt of the Smart Analysis is pseudonymised by `PromptPseudonymiser` (`VENDOR_n`, `MRP_n`, `PGROUP_n`, `MATERIAL_n`, plus the elements above in the comments). The alias → name table stays in memory; aliases in the answer are replaced by the real names before display.
  - Prices and volumes are never part of the prompt (only shares, counts, trends and a few comments).
- **Limits** (thesis 3.8): abbreviated or misspelled supplier names and person names without "@" are not detected; MRP controllers and purchasing groups are replaced in the statistics, not inside free text. Pseudonymisation reduces the risk; it does not replace Roche's approval.

## 📌 Part D: Smart Analysis (LLM)
- **Objective**: A short written analysis of the current selection, from figures that pandas has already computed.
- **Actions** (`scripts/llm_summary.py`):
  - Compact prompt: key statistics (every key states its unit) + the most frequent informative comments of the three main root causes.
  - Five fixed sections: Key findings, Trend over time, Where the issues come from, Risks to escalate, Recommended actions; the answer is streamed.
  - **Cloud** (shown in the dashboard): Mistral API, default model `ministral-14b-latest` (`MISTRAL_MODEL` in `.env`), pseudonymised prompt. Chosen on 16 Oct. so that the app can run on any laptop and be deployed, and the Mac no longer heats up.
  - **Local** (backup, `render_ai_summary("local")`): LM Studio with Mistral 7B Instruct v0.3 (`LM_STUDIO_BASE_URL`, `LM_STUDIO_MODEL` in `.env`); no data leaves the machine.
  - **Notebook** `llm_summary.ipynb`: statistics, prompt, pseudonymised prompt (checks that no real vendor name is sent), then the cloud or local analysis behind a switch (`RUN_CLOUD`, `RUN_LOCAL`), so that Run All calls no model.
- **Tools**: `openai` client (OpenAI-compatible APIs), Mistral API, LM Studio.
- **Output**: the *Smart Analysis* section of the dashboard.

## 📌 Part E: Remote Access for Usability Tests
- **Objective**: Let planners test the dashboard in their own browser with the real data.
- **Actions**: `./share.sh` starts Streamlit and an ngrok tunnel; the app asks for `APP_PASSWORD` (set in `.env`). The data stays on this Mac; the dashboard is reachable only while the script runs.
- **Limits**: one shared password, link changes at each start, third party (ngrok) in the path: acceptable for a short test, not for production. Details in `tools_justification.md`, section 12.

## 📌 Part F: Tests
- **Actions**: `python -m pytest -q tests` (46 tests), synthetic data only, fake API clients: no network, no key, no Roche data.
  - `test_comment_cleaning.py`: journal entries and signatures (chains, typos, `n/a`), snapshot merge (partial week skipped), abbreviations by language, entry-by-entry translation, `Comment_EN` from the cache when saving (no DeepL call), no login in the output.
  - `test_glossary.py`: validation of the glossary, creation and reuse on DeepL, stale translations redone only on request.
  - `test_pseudonymise.py`: identifying elements replaced and restored (DeepL path).
  - `test_cloud_summary.py`: no real name in the Mistral request, aliases restored in the streamed answer.

## 📌 Part G: Insights Lab (new pages, to validate)
- **Objective**: answer the feedback of the tool owner (Johannes Höttler, demo of 23.10: US24 similar comments counted as one issue, US25 problem vs latest entry of a journal, US26 explain weekly changes, root cause × impact) and look for weak signals. The new pages sit in a **second row of the top menu**; the existing page is unchanged until a new page is validated and replaces its section. Changing page is a Streamlit rerun, not a page load: the sidebar filters (which apply to the new pages too) and the password stay; the page is also written in the URL (`?page=...`).
- **Tracking table** (`scripts/tracking.py` → `data/item_tracking.csv`): built from **all** snapshot rows, not only the commented ones. One row per (snapshot day, material, vendor) when the item has a root cause, an impact, a comment or a stock-out status (143,569 item-days, 3,977 items): worst status of its order lines, root cause, most severe impact entered (`None (no impact)` when the planner entered that there is none), cleaned comment (no login). **An empty impact means "not communicated"**: the impact is unknown, which does not mean that there is none; every page and the Smart Analysis say so (`Not communicated`).
- **Pages** (`scripts/insights_pages.py`, analyses in `scripts/insights.py`):
  - *Frequent Comments, Grouped*: near-identical comments counted as one issue, in three explainable rules: same text after normalisation (case, punctuation, *stock-out* / *pull-in* spellings), one wording contained in the other with the same main root cause (`px13` and `px13 - No stockout detected`), similar wording (cosine of character 3-5-grams ≥ 0.55, adjustable) **or similar meaning** (sentence embeddings of a small local language model, *all-MiniLM-L6-v2*, ≥ 0.80) with the same main root cause. A wording joins the most frequent similar one (no chains); the reason of every merge is shown. 1,504 distinct wordings → 1,044 issues (wording) or 1,129 (meaning, stricter but better on paraphrases: *No stockout apparent* / *No stockout detected* 0.89). Groups whose wordings differ only by numbers get a neutral label: `[n] estimated time of arrival [date]`. Option: count only the problem (first written entry) or the latest status (most recent entry): the journal is written newest first (171 cells vs 8).
  - *Root Cause Trends (all snapshots)*: items per root cause (or per stakeholder, prefix of the root cause) and week, from the tracking table; *What changed between two weeks*: items that entered / left Actual (or Potential) Stock Out between two week-end snapshots, by root cause, with their comments.
  - *Root Cause × Impact*: contingency table of the items, chi-square test of independence (p < 0.001, Cramér's V 0.26: moderate association), and per root cause the share of severe impacts (Production + Market), lift and Fisher's exact test.
  - *Weak Signals*: do the first comments of an item announce a Production / Market impact entered later? 1,221 items, 126 severe later, median 20 days of warning. Words with a significant lift (Fisher's exact test: *request pull-in*, *trying to expedite*, *escalated to procurement*), a logistic regression with 5-fold cross-validation scored with the MCC (comment + root cause: MCC ≈ 0.26-0.29, AUC ≈ 0.76; root cause alone: MCC ≈ 0.19), and a watch list of open items ranked by their out-of-fold risk.
- **Literature**: Usuga-Cadavid et al. (*Using deep learning to value free-form text data for predictive maintenance*): on short, code-like texts classic models are as good as transformers; MCC for imbalanced classes; aggregated word contributions as insights. The same choices are made here, so that every result can be explained.
- **Limits**: neither method knows the supply-chain jargon: *expedite* and *pull-in* stay apart (0.20 with the language model). The weak-signal model is trained on few positive items (126): a ranking to look at first, not a forecast. Impacts are mostly entered on Actual Stock Outs (internal rule), so the population is not neutral.

## 🔄 Updating the Data (new snapshots)
Run everything from the project root, with the virtual environment active:
```bash
cd /Users/matthieusanner/Roche_AI_PoC
source venv/bin/activate
```

| Step | Command | What it does |
|------|---------|--------------|
| 1. Add the files | copy the new CSV files into `data/Snapshot_2026/` | Same columns as the existing files; the file name does not matter, days already present are not counted twice. |
| 2. Rebuild (steps 1-6) | `python scripts/data_cleaning.py` (or Run All in `data_cleaning.ipynb`) | Re-reads **all** snapshots and rewrites `data/cleaned_comments.csv` (~30 s): new comments added, `Last_Seen` / `Days_Active` updated, latest root cause and impact taken. |
| 2b. Tracking table | `python scripts/tracking.py` | Re-reads all snapshots and rewrites `data/item_tracking.csv` (~20 s), used by the Insights Lab pages. |
| 3. Translate (step 7) | only if step 2 reports German entries not translated yet: `python scripts/translation.py --dry-run` then `python scripts/translation.py` (or `translation.ipynb`) | The dry run only counts the characters to send. The real run pseudonymises and translates **only the new** German comments (the others come from the cache) and prints the monthly DeepL usage. If interrupted, just run it again. |
| 4. Reload | Streamlit → menu **⋮** → **Clear cache**, then **Rerun** (or `Ctrl + C` and `streamlit run scripts/app.py`) | Streamlit keeps the data in memory: "Rerun" alone does not reload the CSV. |

- Step 2 already fills `Comment_EN` from the translation cache, so after a rebuild the dashboard works at once. Step 3 is needed only for new German entries (step 2 prints their number); until then they appear in German.
- **GitHub**: a data update needs no push. Snapshots, `cleaned_comments.csv`, the translation cache and the saved views are confidential and excluded by `.gitignore`. Only code changes (`scripts/`) are pushed.
- **Keys**: `DEEPL_API_KEY`, `MISTRAL_API_KEY` and `APP_PASSWORD` go in the `.env` file at the project root; `scripts/config.py` reads it. Never commit it.

## 📌 Next Steps
- [x] Improve data cleaning for edge cases (comments without prefix, one row per material and vendor).
- [x] Split the comment journal into entries, remove the signatures (logins), cleaning in seven checkable steps.
- [x] Comment-centred statistics, filters and saved views in the dashboard.
- [x] Pseudonymisation before DeepL and before the Mistral API.
- [x] Smart Analysis with a cloud model; local model kept as backup.
- [ ] Validate with Roche (tool engineer / IT) the use of an external LLM API and the hosting of a demo outside Roche.
- [ ] Check Mistral's data retention and training terms for the plan used, and cite them in the thesis.
- [ ] Revoke the DeepL key that was once pushed to GitHub (it remains in the Git history).
- [ ] Have the DeepL glossary (`lexicon/glossary_de_en.csv`) validated by the planners together with the abbreviations: confirm or correct the English term, set `status`, then `python scripts/translation.py --dry-run` and, if the cost is acceptable, `--refresh-glossary`.
- [ ] Have the abbreviation library validated by the planners (Johannes and Alexis): Excel sheet `data/interim/abbreviations_for_review.xlsx` (step 6b of `data_cleaning.ipynb`); start with the low-confidence abbreviations, `LT` first.
- [ ] Evaluate the Smart Analysis (are the figures and quotes faithful? compare cloud vs local on the same selections); no formal evaluation exists yet.
- [x] Tracking table for the trends over time (root cause, impact, status per snapshot, also without comment).
- [ ] Validate the Insights Lab pages, then let them replace the sections of the main page.
- [x] Group paraphrases by meaning (local language model, all-MiniLM-L6-v2).
- [ ] Jargon synonyms (*expedite* / *pull-in*): a small synonym list validated by the planners, if needed.
- [ ] Improve the language detection of short mixed entries (step 5).
- [ ] Deepen NLP analysis (keyword extraction, root cause correlations); add word clouds / heatmaps.
- [ ] If Roche adopts the dashboard: rebuild it on an internal platform (e.g., R Shiny, Posit Connect).

# Architecture

## 1. Principle

> **Statistics first (pandas), classical NLP for text structure, local LLM only for wording.**

The dashboard must already be useful with no AI: for any supplier, MRP controller or material it shows
where to look, what happened in the past and which root causes dominate. The LLM then phrases an
already-computed profile; it never counts, and every number it cites is checked against the facts.

## 2. Layers (each depends only on the ones above it)

```
config  ->  data  ->  stats  ->  nlp  ->  llm / ml        dashboard (thin consumer)
```

| Package | Role | Deterministic? |
|---|---|---|
| `roche_poc.config` | paths, column names, statuses, alert thresholds, service settings | yes |
| `roche_poc.data` | load raw CSV snapshots, clean, build `snapshots` and `comments` tables | yes |
| `roche_poc.stats` | KPIs, persistence, trends, watchlist rules, **one profile for every level** | yes |
| `roche_poc.nlp` | language detection, DE->EN translation, lemmatisation, TF-IDF keywords | yes (cached) |
| `roche_poc.llm` | LM Studio client, prompts, summary, number validation | no (validated) |
| `roche_poc.ml` | empty: predictive analytics, later | - |

**Notebooks drive, `.py` files hold the logic.** A function exists in exactly one place; notebooks and
dashboard import it. Notebooks are for exploration, validation and thesis figures only.

## 3. The two tables (the key design decision)

| Table | Grain | Used for |
|---|---|---|
| `snapshots` | one row per (snapshot, MRP element) | **all statistics**, persistence, trends, future ML |
| `comments` | one row per unique (material, comment), with `first_seen`, `last_seen`, `n_snapshots` | NLP, translation, LLM context |

The first prototype computed statistics on de-duplicated comments only. A comment that persisted for ten
weeks was counted once, so the "trend" (-91 %) measured the arrival of *new* comments, not the real
situation. Statistics now use `snapshots`; deduplication happens only in the `comments` table, and only
for text analysis. Counts are *element-snapshots* (exposure): a problem lasting ten weeks weighs ten times
a one-week problem; distinct material counts are reported next to them.

## 4. One profile for every level

`stats.profile.build_profile(snapshots, comments, level, entity_id)` takes `level` in
`vendor | mrp_controller | material` and always returns the same JSON-safe dictionary:
`meta, current, history, root_causes, persistence, watchlist, recent_comments` plus
`top_materials` (vendor, MRP controller) or `related_vendors` (material).

The dashboard renders it with one function (`dashboard/components/entity_view.py`); the three pages differ
only by their selector. The same dictionary, reduced to compact facts, feeds the LLM prompt.

## 5. Watchlist rules (all thresholds in `config.py`)

| Rule | Trigger | Severity |
|---|---|---|
| Escalate | Actual Stock Out with Production or Market impact (Supply Risk Meeting criterion) | high |
| Chronic | critical for >= `PERSISTENT_CRITICAL_SNAPSHOTS` consecutive snapshots | high |
| Governance | critical without root cause / without comment | medium |
| Recurrent | >= `RECURRENT_EPISODES` separate critical episodes | medium |
| Delivery | `Delay` > `LONG_DELAY_DAYS` on a critical element (unit to confirm) | medium |

Trend labels use a least-squares slope over all snapshots and refuse to conclude below
`MIN_POINTS_FOR_TREND` points (the old first-vs-last comparison rested on two points).

## 6. NLP versus LLM

| Task | Tool | Why |
|---|---|---|
| language detection, translation, lemmatisation, keywords per root cause | NLP | reproducible, measurable |
| sub-themes inside a root cause (`nlp/themes.py`, empty) | embeddings + clustering | measurable (silhouette), LLM only names clusters |
| narrative summary of a profile | local LLM | what a language model does best; figures validated |

## 7. Data governance

* Raw data, processed tables and `.env` are git-ignored (root `.gitignore`).
* The LLM runs locally (LM Studio): no data leaves the machine.
* DeepL is a **cloud** service: German planner comments are sent to it. This inconsistency with the
  "local LLM" argument must be stated in the Discussion/Limits chapter (alternatives: pseudonymised data,
  agreement with Roche, or translation by the local model with a measured quality loss).
* Known limit of the number check: it detects invented numbers, not a correct number attached to the
  wrong entity.

## 8. Migration map (previous prototype -> this structure)

| Previous | Now |
|---|---|
| `scripts/data_cleaning.ipynb` | `data/loading.py`, `data/cleaning.py`, `data/build_tables.py`, `notebooks/01_data_build.ipynb` |
| `scripts/translation.ipynb` | `nlp/language.py`, `nlp/translation.py`, `notebooks/03_nlp_translation.ipynb` |
| `scripts/nlp_analysis.ipynb` | `nlp/preprocessing.py`, `nlp/keywords.py` |
| `scripts/stats_engine.py` | `stats/` (kpis, persistence, trends, watchlist, profile) |
| `scripts/llm_summary.py` + notebook | `llm/` + `notebooks/04_llm_summary.ipynb` |
| `scripts/app.py` (single file, tabs) | `dashboard/Home.py`, `pages/`, `components/` |
| `scripts/config.py` (API key in clear text) | `config.py` (no secret) + `.env` |
| `scripts/nlp_pipeline.py`, `scripts/data_cleaning.py`, `outputs/visualization.py` | removed (synthetic-data prototype, French `PhraseMatcher`; root causes are entered by buyers) |
| old notebooks | `notebooks/_legacy/` (kept for reference; their saved outputs contain real comments) |

## 9. Known limits and next steps

* Comments may contain several time-stamped entries in one cell; only the leading prefix is removed. Splitting
  entries would give one dated row per comment.
* `Delay` unit and the MRP element key (plant, PO, schedule line) must be confirmed with the data owner.
* The pipeline has been tested on synthetic data only (`tests/`); first run on the real data needs a check
  of column names against `config.py`.

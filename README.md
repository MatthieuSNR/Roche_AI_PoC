# Roche AI PoC: Material Availability Dashboard

Statistics-first analytics on weekly material-availability snapshots, with classical NLP for the
planner comments and a **local** LLM (LM Studio) that phrases the computed facts.
Design rationale: [docs/architecture.md](docs/architecture.md).

## Structure

```
src/roche_poc/        the engine (no Streamlit dependency)
  config.py           paths, columns, statuses, thresholds
  data/               loading, cleaning, build_tables  -> snapshots + comments tables
  stats/              kpis, persistence, trends, watchlist, profile
  nlp/                language, translation (DeepL), preprocessing, keywords, themes (empty)
  llm/                client, prompts, summary, validation
  ml/                 (empty) predictive analytics, later
dashboard/            Streamlit multipage app: Home + Supplier / MRP controller / Material / AI summary
notebooks/            01 data build · 02 statistics · 03 NLP · 04 LLM · 05 ML (empty) · _legacy
tests/                synthetic fixtures, no Roche data
data/                 raw/ interim/ processed/  (git-ignored: confidential)
docs/                 architecture, tools justification, project steps
```

Notebooks drive, `.py` files hold the logic: nothing is defined twice.

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && pip install -e .
python -m spacy download en_core_web_sm        # only needed for lemmatisation
cp .env.example .env                           # then fill DEEPL_API_KEY

# 1. put the raw snapshot CSVs in data/raw/Snapshot_2026/
python -m roche_poc.data.build_tables          # -> data/processed/*.parquet
# 2. (optional) translate German comments: notebooks/03_nlp_translation.ipynb
# 3. dashboard
streamlit run dashboard/Home.py
```

AI summary: start LM Studio (Developer tab -> *Server: Running*, port 1234), load the model, open the
*AI Summary* page. The base URL must end with `/v1` (see `.env.example`).

## Tests

```bash
pytest                      # or: python tests/run_tests.py  (no pytest needed)
```

## Security

* Never commit `.env`, `data/` or notebook outputs containing comments (the root `.gitignore` excludes
  the first two; clear notebook outputs, e.g. with `nbstripout`, before pushing).
* If a key was ever committed, revoking it is mandatory: deleting the file does not remove it from git history.

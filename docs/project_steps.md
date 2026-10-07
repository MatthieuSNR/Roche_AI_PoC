# Project steps

| # | Step | Code | Status |
|---|---|---|---|
| 1 | Build `snapshots` and `comments` tables from raw CSVs | `roche_poc.data`, notebook 01 | done (synthetic tests) |
| 2 | Statistics layer: KPIs, persistence, trends, watchlist, profile | `roche_poc.stats`, notebook 02 | done (synthetic tests) |
| 3 | Dashboard: portfolio, supplier, MRP controller, material | `dashboard/` | done (to run on real data) |
| 4 | NLP: language, translation, keywords per root cause | `roche_poc.nlp`, notebook 03 | translation/keywords done |
| 5 | Local LLM summary + number validation | `roche_poc.llm`, notebook 04 | done (needs LM Studio) |
| 6 | Sub-themes by embeddings + clustering | `nlp/themes.py` | empty |
| 7 | Predictive analytics | `roche_poc.ml`, notebook 05 | empty |
| 8 | Evaluation: unsupported-number rate per model, rule precision with Roche users | notebook 04 | to do |

# 🛠️ Tools and Libraries Justification

This document justifies the **selection of tools, libraries, and frameworks** used in the **Roche AI PoC: Material Availability Dashboard Optimization** project.
Each choice is grounded in **technical requirements, academic standards, and industry best practices** to ensure **reproducibility, scalability, and maintainability**.

---

---

## **📌 1. Programming Language: Python (v3.12.4)**

### **Why Python?**
   **Criteria**          | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **Industry Standard** | Python is the **most widely used language** for **NLP (Natural Language Processing)** and **Machine Learning (ML)** in both academia and industry (e.g., [Stack Overflow Survey 2023](https://survey.stackoverflow.co/2023/)). |
 | **Library Ecosystem** | Rich ecosystem of **open-source libraries** (e.g., `pandas`, `spaCy`, `scikit-learn`) tailored for data science and NLP tasks.                                                                               |
 | **Readability**       | Clean and **intuitive syntax**, making it easier to document and share code (critical for thesis reproducibility).                                                                                           |
 | **Compatibility**     | Version **3.12.4** ensures compatibility with all required libraries (e.g., `spaCy 3.8.16`, `pandas 2.2.3`).                                                                                     |
 | **Academic Adoption** | Python is **the most cited language** in NLP/ML research papers (e.g., [arXiv](https://arxiv.org/), [ACL Anthology](https://aclanthology.org/)).                                                                   |

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason**                                                                                     |
 |-----------------|-------------------------------------------------------------------------------------------------------|
 | R               | Strong in statistics but **less suited for NLP/ML pipelines** and lacks native spaCy/scikit-learn support. |
 | Java            | Verbose syntax and **steeper learning curve** for data science tasks.                              |
 | JavaScript      | Limited **NLP/ML libraries** compared to Python.                                                     |

### **References**
- [Python Official Documentation](https://www.python.org/doc/)
- [Stack Overflow Developer Survey 2023](https://survey.stackoverflow.co/2023/)
- [arXiv: Python in NLP Research](https://arxiv.org/)

---

---

## **📌 2. Integrated Development Environment (IDE): Visual Studio Code (VS Code)**

### **Why VS Code?**
 | **Criteria**          | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **Python Support**    | Built-in **Python extension** (Pylance) for autocompletion, linting, and debugging.                                                                                                                             |
 | **Lightweight**       | Faster and **less resource-intensive** than alternatives like PyCharm.                                                                                                                                       |
 | **Git Integration**   | Native **Git support** for version control, critical for collaborative projects.                                                                                                                               |
 | **Extensions**        | Rich marketplace (e.g., **Jupyter Notebooks**, **Mermaid**, **GitLens**) to enhance productivity.                                                                                                               |
 | **Cross-Platform**    | Works seamlessly on **macOS, Windows, and Linux**.                                                                                                                                                              |
 | **Academic Use**      | Widely adopted in **universities and research** for data science projects.                                                                                                                                |

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason**                                                                                     |
 |-----------------|-------------------------------------------------------------------------------------------------------|
 | PyCharm         | Heavy and **slower** for small projects like this PoC.                                              |
 | Jupyter Notebook | Limited **file management** and less suitable for script-based workflows.                          |
 | Sublime Text    | Lacks **native Python debugging** and Git integration.                                             |

### **References**
- [VS Code Official Documentation](https://code.visualstudio.com/docs)
- [Stack Overflow Survey 2023: Most Popular IDEs](https://survey.stackoverflow.co/2023/)

---

---

## **📌 3. Data Manipulation: pandas (v2.2.3)**

### **Why pandas?**
 | **Criteria**          | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **Industry Standard** | **De facto standard** for data manipulation in Python (used by 80% of data scientists, per [Kaggle Surveys](https://www.kaggle.com/surveys)).                                                           |
 | **Performance**       | Optimized for **large datasets** with C-based backend.                                                                                                                                                         |
 | **Functionality**     | Provides **DataFrame** structure for easy cleaning, filtering, and aggregation.                                                                                                                               |
 | **Integration**       | Works seamlessly with **spaCy, scikit-learn, and matplotlib**.                                                                                                                                                   |
 | **Academic Use**      | Cited in **thousands of research papers** (e.g., [Nature](https://www.nature.com/), [IEEE](https://ieeexplore.ieee.org/)).                                                                                     |

### **Key Features Used in the Project**
- **`pd.read_csv()` + `glob`**: Load the 174 daily snapshots of `data/Snapshot_2026/` (≈2 million rows, only the ≈88,000 commented rows are kept).
- **`groupby().agg()`**: One row per (material, vendor, comment) with `First_Seen`, `Last_Seen`, `N_Snapshots`, `Days_Active`.
- **`to_datetime()`**: Convert snapshot dates to datetime objects (period filters, weekly trends).
- **`value_counts()` / `groupby()`**: All dashboard statistics (`scripts/stats_engine.py`), e.g. "X% of this vendor's comments have root cause Y".

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason**                                                                                     |
 |-----------------|-------------------------------------------------------------------------------------------------------|
 | Polars          | Faster but **less mature** and lacks some pandas features (e.g., seamless integration with scikit-learn). |
 | Dask            | Overkill for **medium datasets** (≈2 million snapshot rows, read in ≈15 s; ≈2,300 comments after cleaning). |
 | R (data.table)  | Not compatible with **Python-based NLP libraries** like spaCy.                                       |

### **References**
- [pandas Official Documentation](https://pandas.pydata.org/docs/)
- [Kaggle: State of Data Science 2023](https://www.kaggle.com/surveys/2023)

---

---

## **📌 4. Natural Language Processing (NLP): spaCy (v3.8.16)**

### **Why spaCy?**
 | **Criteria**          | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **Performance**       | **Faster** than NLTK for tokenization, lemmatization, and entity recognition.                                                                                                                                   |
 | **Multilingual**      | Supports **German (`de_core_news_sm`)** and **English (`en_core_web_sm`)**, the two languages of the planner comments.                                                                                               |
 | **Pre-trained Models**| Includes **pre-trained models** for NLP tasks (e.g., entity recognition, dependency parsing).                                                                                                               |
 | **Industry Adoption** | Widely used in **industrial NLP pipelines** (production-oriented design, maintained by Explosion AI).                                                                                                              |
 | **Academic Use**      | Cited in **NLP research** (e.g., [ACL Anthology](https://aclanthology.org/)).                                                                                                                                     |

### **Key Features Used in the Project**
- **Tokenization**: Split text into words/tokens.
- **Lemmatization**: Reduce words to their base form (e.g., "ruptures" → "rupture").
- **Stop Word Removal**: Filter out common words (e.g., "the", "und").
- **Keyword analysis by root cause** (exploration notebook `data_cleaning.ipynb`).

### **Alternatives Considered**
 | **Alternative**       | **Rejection Reason**                                                                                     |
 |-----------------------|-------------------------------------------------------------------------------------------------------|
 | NLTK                  | **Slower** and less optimized for German.                                                             |
 | Hugging Face Transformers | Overkill for **simple NLP tasks** (e.g., root cause extraction). Requires GPU for large models. |
 | Stanford NLP          | **Java-based**, not compatible with Python workflows.                                               |

### **References**
- [spaCy Official Documentation](https://spacy.io/)
- [spaCy Models: German and English](https://spacy.io/models)
- [ACL Anthology: spaCy in Research](https://aclanthology.org/)

---

---

## **📌 5. Language Detection and Translation: langdetect (v1.0.9) + DeepL API (deepl v1.32.0)**

### **Why langdetect + DeepL?**
 | **Criteria**          | **Justification** |
 |-----------------------|-------------------|
 | **Need**              | About two thirds of the planner comments are written in **German**; translating them to English gives one language for analysis, dashboard and LLM summary. |
 | **Translation quality** | DeepL handles **German supply-chain jargon and abbreviations** (e.g., "best. LT", "Stk") better than generic free tools. |
 | **Cost control**      | Only German comments are sent, and every translation is stored in `data/interim/translation_cache.csv`: a comment is **paid for only once**, even after a data rebuild. A `--dry-run` mode counts the characters before sending (free plan: 500,000 characters/month). |
 | **Detection accuracy** | `langdetect` alone labelled short German comments as Hungarian, Catalan, Norwegian… (≈12 %), and these were never translated. Detection is therefore **restricted to English/German**, with a small German lexicon as fallback. |

### **Key Features Used in the Project** (`scripts/translation.py`)
- **`detect_langs()`**: Language probabilities, reduced to `en` / `de`.
- **`Translator.translate_text()`**: Batch translation (50 comments per call), with retry on rate limit.
- **`Translator.get_usage()`**: Monthly character usage, printed after each run.

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason** |
 |-----------------|----------------------|
 | Google Translate API | Comparable quality but **paid from the first character** and less precise on technical German. |
 | Local translation model (e.g., MarianMT, Hugging Face) | **No data leaves the machine**, but lower quality on jargon and slower on CPU; a possible option if data governance requires it. |
 | Local LLM (LM Studio) | Possible, but **slower** and less consistent than a dedicated translation engine. |

### **Data Governance**
DeepL is a **cloud service**: only the comment text is sent (no vendor, material or quantity column). Before sending, the text is **pseudonymised** (`scripts/pseudonymise.py`): e-mail addresses, @-mentions, supplier names, material numbers, long numbers (PO, batch) and the company name are replaced by placeholders, which DeepL copies unchanged; the original values are restored locally after translation. The same module protects the prompt of the Smart Analysis (section 6).

**Residual limits** (thesis, 3.8):
- Supplier names written in an **abbreviated or misspelled** form, and supplier names shorter than 4 characters, are not detected.
- **Person names** written without "@" or e-mail address (e.g., "laut Hr. Müller") are not detected.
- The **rest of the comment** (delays, quantities, problem descriptions) is still sent to a cloud service; pseudonymisation reduces, but does not remove, the governance question. The local alternatives above remain possible.
- The placeholder pattern relies on DeepL respecting the ignored tags; a placeholder that is altered would not be restored (checked by `tests/test_pseudonymise.py` for the local part only).

### **References**
- [DeepL API Documentation](https://developers.deepl.com/docs)
- [langdetect (port of Google's language-detection)](https://pypi.org/project/langdetect/)

---

---

## **📌 6. Smart Analysis: Mistral API (cloud) with a local LLM as backup (LM Studio)**

### **What the LLM does, and what it does not**
**pandas computes every number** (`scripts/stats_engine.py`); the LLM only **writes** the analysis from these precomputed statistics and the most frequent comments, and is instructed never to compute or invent a figure. This is why a small model is sufficient and why the figures of the analysis can be checked against the dashboard.

### **Why the Mistral API (since 16 Oct.)?**
 | **Criteria**          | **Justification** |
 |-----------------------|-------------------|
 | **Need**              | The local model (Mistral 7B on the laptop) took 40–60 s per analysis, made the Mac heat up, and cannot run on a deployed or shared app. A hosted model removes the load from the laptop. |
 | **Same family, same interface** | Mistral's API is **OpenAI-compatible**: the same `openai` client and the same prompt are used (only `MISTRAL_BASE_URL` and the key change), so cloud and local answers can be compared on the same selections. |
 | **Model**             | `ministral-14b-latest` by default (`MISTRAL_MODEL` in `.env`). On the free plan, the small and medium models were often rate-limited (HTTP 429) and the large one not included (HTTP 403) when tested on 16 Oct.; this choice is a practical one and may change with the plan. |
 | **Provider**          | European provider, free tier sufficient for a prototype. For an adoption by Roche, the choice would follow the contract Roche has already approved (e.g., a model hosted in an EU region by a provider under Roche's agreement). |
 | **Cost**              | Negligible at this volume (one request of about 1,000 input tokens per analysis); the free plan quotas are shared by all visitors of a shared demo. |

### **Key Features Used in the Project** (`scripts/llm_summary.py`, `scripts/pseudonymise.py`)
- **`chat.completions.create()`** with low temperature (0.2) for factual answers; the same prompt for cloud and local (`build_prompt`).
- **Compact prompt** (`build_facts`): only the key statistics, without indentation or duplicated figures, and every key states its unit (`_pct` = percentage, otherwise a count) after the model turned "+75 comments" into "+75%" in a test.
- **Structured, in-depth analysis**: 250–350 words in five fixed sections (Key findings, Trend over time, Where the issues come from, Risks to escalate, Recommended actions). The prompt includes the most frequent informative comments of the three main root causes, and the model must quote at least one comment word for word, so the analysis explains *why* and not only *how much*.
- **Streaming** (`stream_summary_cloud`): the analysis appears word by word.
- **Pseudonymised prompt** (`PromptPseudonymiser`): suppliers, MRP controllers, purchasing groups and material numbers are replaced by aliases (`VENDOR_1`, `MRP_2`, `PGROUP_3`, `MATERIAL_4`), and e-mails, @-mentions, long numbers and the company name in the comments too. The prompt tells the model to copy the aliases unchanged. The alias table stays in memory on the Mac; aliases in the answer are replaced by the real names before display (`stream_restored` holds back the last word so that half an alias is never shown). Pseudonymisation is always on for the cloud model.
- **Nothing else is sent**: no price and no volume; only shares, counts, trends and a few short comments. A test (`tests/test_cloud_summary.py`) checks that no real supplier, MRP controller, purchasing group, material number or e-mail appears in the request, and that the answer comes back with the real names.

### **Data Governance and Limits**
- **Pseudonymisation is a safeguard, not an approval**: the use of an external LLM API on Roche data has still to be validated with Roche (open point). Business-confidential content (shares per supplier, planner comments) leaves the machine in aliased form.
- **Residual limits** are those of section 5: supplier names written in abbreviated or misspelled form and person names without "@" are not detected; MRP controllers and purchasing groups are short codes, replaced in the statistics but not searched inside free text.
- **Provider terms**: Mistral's retention and training terms for the plan in use have not been verified yet; they must be checked and cited before the thesis states that the data is not stored.
- **Quality**: LLM output is not deterministic and there is no formal evaluation yet (faithfulness of figures and quotes, comparison cloud vs local). The figures are protected by construction (pandas), the interpretation is not.
- **Availability**: the cloud analysis needs the network and a valid key; the free plan can answer 429 under load.

### **Local backup: LM Studio (Mistral 7B Instruct v0.3)**
 | **Criteria**          | **Justification** |
 |-----------------------|-------------------|
 | **Confidentiality**   | The model runs **on the laptop** (`http://127.0.0.1:1234/v1`): no Roche data leaves the machine. Still the reference if data governance forbids any external API. |
 | **Cost**              | No API fee, no usage limit. |
 | **Limits**            | ≈5 tokens/s on an Apple M3 with 16 GB when memory is short, so 40–60 s per analysis and a hot laptop; Mistral 7B does not accept the `system` role (instructions are merged into the user message). |
 | **Status**            | Kept in the code (`stream_summary`, `render_ai_summary("local")`, `is_server_available`) but no longer shown in the dashboard. |

### **Alternatives Considered**
 | **Alternative** | **Reason** |
 |-----------------|-----------|
 | Other cloud APIs (OpenAI, Anthropic, Azure OpenAI, AWS Bedrock, Google Vertex AI) | Comparable quality for this task, so the choice depends on data governance and contracts rather than benchmarks. Not retained for the prototype; the code only needs another base URL and key. Under an existing Roche agreement, one of these (EU region) would be the natural choice. |
 | Local only (LM Studio, Ollama) | Best confidentiality but slow, hot laptop, impossible to deploy or share. Ollama is equivalent to LM Studio; LM Studio was chosen for its graphical interface. |
 | Larger local models (≥ 13B) | Too slow on a laptop for an interactive dashboard. |

### **References**
- [Mistral AI Documentation](https://docs.mistral.ai/)
- [LM Studio Documentation](https://lmstudio.ai/docs)
- [Mistral 7B Instruct v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3)
- [GDPR (Regulation (EU) 2016/679), Art. 4(5): definition of pseudonymisation](https://eur-lex.europa.eu/eli/reg/2016/679/oj)


## **📌 7. Visualization: matplotlib (v3.8.4) + seaborn (v0.13.2)**

### **Why matplotlib + seaborn?**
 | **Tool**       | **Justification**                                                                                                                                                                                                 |
 |----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **matplotlib** | **Standard library** for basic plots (histograms, bar charts). **Integrated with pandas** (e.g., `df.plot()`).                                                                                                   |
 | **seaborn**    | **Enhanced aesthetics** for statistical plots (e.g., heatmaps, boxplots). Built on top of matplotlib.                                                                                                               |

### **Key Features Used in the Project**
- **Bar Charts**: Top root causes with count and share of the selection.
- **Pie Charts**: Root cause share.
- **Line Charts**: Weekly trend of the comments per root cause.
- **Heatmaps** (seaborn, notebook): Root causes per vendor.

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason**                                                                                     |
 |-----------------|-------------------------------------------------------------------------------------------------------|
 | Plotly          | **Interactive** but heavier and requires JavaScript for full functionality.              |
 | ggplot          | **R-based**, not compatible with Python.                                                             |

### **References**
- [matplotlib Official Documentation](https://matplotlib.org/stable/contents.html)
- [seaborn Official Documentation](https://seaborn.pydata.org/)

---

---

## **📌 8. Dashboard: Streamlit (v1.32.0)**

### **Why Streamlit?**
 | **Criteria**          | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **Ease of Use**       | **No frontend development** required. Write Python scripts and get a **fully interactive web app**.                                                                                                             |
 | **Integration**       | Works with **pandas, matplotlib, and scikit-learn** out of the box.                                                                                                                                               |
 | **Deployment**        | Free hosting on [Streamlit Cloud](https://streamlit.io/cloud) is possible, but not used with the confidential data (see section 12).                                                                                                                                             |
 | **Industry Adoption** | Widely used by **data science teams** for internal prototypes (acquired by Snowflake in 2022).                                                                                                                      |
 | **Academic Use**      | Increasingly used in **research** for sharing interactive results (e.g., [arXiv](https://arxiv.org/)).                                                                                                         |

### **Key Features Used in the Project**
- **Widgets**: Sidebar filters (MRP controller, purchasing group, vendor, material, root cause, impact, period); every filter is a **multiselect** (empty = All), so a planner can view their own scope plus the colleagues they back up (user feedback, demo of 16 Oct.). The filters **cascade**: each one only offers the values that exist within the filters above it (e.g. only the vendors of the selected MRP controllers).
- **Saved views** (like SAP *personalised views*): the current filters, period and table columns can be saved under a name and re-applied in one click by any user (stored on the Mac in `data/interim/saved_views.json`, not pushed to GitHub). The columns of the comments table are set in a **▥ Columns** panel (toggle on the right, stays open until the user closes it): a checkbox per column to show or hide it, and **drag and drop** to change the order ([streamlit-sortables](https://github.com/ohtaman/streamlit-sortables), since Streamlit 1.32 has no built-in column menu).
- **Top 5 / 10 / 20** of the root cause and frequent comment sections: a "Select a view" dropdown, same look as "Select a root cause" in the section below.
- **Folding sidebar**: Views, Filters and Timeframe are menus that fold (`st.expander`, fixed titles without emojis), so every filter fits on one screen without scrolling (feedback from the first remote test).
- **One scrolling page**: an overview (ION material status tiles) followed by 7 analysis sections (comments, root causes, frequent comments, root cause details, trends, statistics, Smart Analysis), with a menu that stays at the top of the page to jump to a section.
- **DataFrames**: Display cleaned data and results.
- **Plots**: Render matplotlib/seaborn visualizations.
- **`st.cache_data`**: The comments file is read once, not at every click.
- **Theme + custom CSS** (`.streamlit/config.toml`, `scripts/ui.py`): a look close to the existing Roche **ION Material Availability** dashboard (Roche logo, blue panel headers, square corners, material status tiles), so planners recognise the tool. The logo is in `assets/roche_logo.png`.

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason**                                                                                     |
 |-----------------|-------------------------------------------------------------------------------------------------------|
 | Dash (Plotly)   | **More complex** to set up for simple dashboards.                                                     |
 | Flask/Django    | Requires **HTML/CSS/JavaScript knowledge** for frontend development.                                  |

### **References**
- [Streamlit Official Documentation](https://docs.streamlit.io/)
- [Streamlit Gallery](https://streamlit.io/gallery)

---

---

## **📌 9. Virtual Environment: `venv`**

### **Why a Virtual Environment?**
 | **Criteria**          | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **Isolation**         | Ensures **dependencies for this project** (e.g., `spaCy 3.8.16`) do not conflict with other Python projects.                                                                                                       |
 | **Reproducibility**   | **`requirements.txt`** allows others to recreate the exact same environment.                                                                                                                                   |
 | **Portability**       | Can be **shared across machines** (e.g., your laptop, Roche’s servers).                                                                                                                                             |
 | **Version Control**   | Avoids issues with **multiple Python versions** (e.g., Python 3.9 vs. 3.12).                                                                                                                                       |

### **How It Was Implemented**
1. **Creation**:
   ```bash
   python3.12 -m venv venv

2. **Activation**:
    ```bash
    source venv/bin/activate

3. **Dependency Intallation**:
    ```bash
    pip install -r requirements.txt

4. **Deactivation**:
    ```bash
    deactivate

### **References**
- [Virtual Environments and Packages](https://docs.python.org/3/tutorial/venv.html)


---
---

## **📌 10. Secrets Management: `.env` file + python-dotenv (v1.2.4)**

### **Why?**
 | **Criteria**          | **Justification** |
 |-----------------------|-------------------|
 | **Security**          | The secrets are stored in a local `.env` file, **excluded from Git** by `.gitignore`: `DEEPL_API_KEY` (translation), `MISTRAL_API_KEY` (Smart Analysis) and `APP_PASSWORD` (password page of the shared app). `scripts/config.py` and `scripts/llm_summary.py` only read them, so the code can be pushed to GitHub without any key. |
 | **Simplicity**        | One file to edit when a key changes; `.env.example` documents the expected variables (`LM_STUDIO_*` and `MISTRAL_MODEL` are settings, not secrets). |

### **Lesson Learned**
An earlier version stored the key directly in `scripts/config.py`, which was pushed to GitHub. A key that has been pushed must be **revoked**: deleting the file does not remove it from the Git history.

### **References**
- [python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [GitHub: Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)


## **📌 11. Project Structure: Why This Organization?**

### **Why This Structure?**
The project follows a **modular and scalable** structure inspired by **best practices in data science** (e.g., [Cookiecutter Data Science](https://drivendata.github.io/cookiecutter-data-science/)).
Each folder and file has a **clear purpose**, making the project **easy to maintain, debug, and extend**.
   **Folder/File**       | **Purpose**                                                                                     | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | `data/`               | **Input data**: daily snapshots, cleaned comments, translation cache (never pushed to GitHub)   | **Separation of concerns**: Raw data is isolated from scripts and outputs to avoid confusion.                                                                                                               |
 | `scripts/`            | **Python scripts** for the PoC (cleaning, NLP, visualization, dashboard)                          | **Modularity**: Each script has a **single responsibility**: `data_cleaning.py` (build the comments file), `translation.py` (DeepL), `pseudonymise.py` (hides names before DeepL / Mistral), `stats_engine.py` (statistics), `llm_summary.py` (Smart Analysis), `ui.py` (layout), `app.py` (dashboard). |
 | `tests/`              | **pytest tests** (pseudonymisation, cloud summary)                                              | **Trust**: the privacy guarantee (no real name in the request) is checked automatically, with fake API clients and no Roche data. |
 | `assets/`, `.streamlit/` | **Roche logo, favicon, theme**                                                               | **Recognition**: a look close to the existing ION dashboard, kept out of the code. |
 | `share.sh`            | **Shares the dashboard through ngrok** (usability tests)                                         | **Control**: one command, refuses to start without a password (section 12). |
 | `outputs/`            | **Generated outputs** (e.g., cleaned data, visualizations, models)                              | **Reproducibility**: Outputs are saved separately to avoid overwriting and to track progress.                                                                                                                                 |
 | `venv/`               | **Virtual environment** for Python dependencies                                                | **Isolation**: Ensures dependencies (e.g., `spaCy 3.8.16`) do not conflict with other projects or system-wide Python.                                                                                              |
 | `docs/`               | **Project documentation** (this file, `project_steps.md`, `projected_project_structure.md`)                                | **Clarity**: Centralizes all documentation for easy reference by stakeholders (e.g., Roche team) and for your thesis.                                                                                              |
 | `requirements.txt`    | **List of Python dependencies**                                                               | **Reproducibility**: Allows others to recreate the exact same environment using `pip install -r requirements.txt`.                                                                                                         |
 | `README.md`           | **Project overview and instructions**                                                          | **Onboarding**: Helps new users (e.g., Roche stakeholders or thesis reviewers) understand how to run the project.                                                                                                  |

---
### **How the Structure Supports the PoC Goals**
1. **Clarity**:
   - Each folder/file has a **clear name and purpose** (e.g., `nlp_pipeline.py` for NLP tasks).
   - **Easy to navigate** for both developers and stakeholders.

2. **Reproducibility**:
   - **`requirements.txt`** and **`venv/`** ensure the project can be **recreated on any machine**.
   - **Scripts can be re-run** at each new snapshot delivery (see `docs/project_steps.md`).

3. **Scalability**:
   - **Modular scripts** (e.g., `data_cleaning.py`, `nlp_pipeline.py`) can be **extended or replaced** without affecting the entire project.
   - **Outputs are separated** from inputs, making it easy to **add new data or scripts**.

4. **Collaboration**:
   - **Git-friendly**: The structure is compatible with **version control** (e.g., Git).
   - **Documentation is centralized** in `docs/`, making it easy to share with Roche or thesis reviewers.

---
### **References**
- [Cookiecutter Data Science Project Template](https://drivendata.github.io/cookiecutter-data-science/)
- [Good Enough Practices in Scientific Computing (arXiv)](https://arxiv.org/abs/1609.00037)
- [Google’s Rules for Repository Structure](https://github.com/google/styleguide/blob/gh-pages/docguide/style.md#repository-structure)



---

---

## **📌 12. Remote Access for Usability Testing: ngrok (v3.20.0, free plan)**

### **Why ngrok?**
 | **Criteria**          | **Justification** |
 |-----------------------|-------------------|
 | **Need**              | Usability tests with planners who are **not next to the laptop**: they open the dashboard in their own browser, with the real data. |
 | **Confidentiality**   | The app keeps running **on this Mac**: the data (`data/cleaned_comments.csv`) is never copied to a cloud server. ngrok only forwards the browser traffic (HTTPS) to `localhost`. |
 | **Effort**            | One command (`./share.sh`), no server, no deployment, no change to the code of the dashboard. Suited to a **prototype**: if Roche adopts the dashboard, it will be rebuilt on an internal platform (e.g., R Shiny, Posit Connect). |
 | **Cost**              | Free plan: one tunnel at a time, a new link at each start. |

### **How It Works in the Project**
- **`share.sh`** (project root): starts Streamlit on port 8505 and an ngrok tunnel to it; `caffeinate` keeps the Mac awake while the app is shared. Ctrl+C stops both.
- **Password page** (`check_password` in `scripts/app.py`): active when `APP_PASSWORD` is set in `.env`, since anyone with the link could otherwise see the data. `share.sh` refuses to start without a password. Empty password = local use, no page.
- The visitor first sees an **ngrok warning page** (free plan) and clicks *Visit Site*, then enters the password.

### **Limits**
- The dashboard is reachable **only while the Mac is on, connected and `share.sh` runs**.
- The traffic goes through **ngrok's servers** (encrypted HTTPS, but a third party in the path); acceptable for a short test with a password, not for production use.
- A simple shared password, no individual accounts; the link changes at each start, which limits its reuse.
- Corporate networks may block `*.ngrok-free.app` domains: test with one colleague before a session.
- Each cloud AI summary generated by a visitor uses the Mistral API key of this Mac (free plan quotas are shared).

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason** |
 |-----------------|----------------------|
 | Streamlit Community Cloud | Free and permanent, but the **confidential data would have to be uploaded** to an external server (the GitHub repository is public). |
 | Internal Roche hosting (Posit Connect, Streamlit in Snowflake...) | The right option for an adopted tool, but requires IT approval: too heavy for a prototype test. |
 | Cloudflare Tunnel / Tailscale | Equivalent tunnels; ngrok was already installed and configured. Tailscale would also require every tester to install a client. |

### **References**
- [ngrok Documentation](https://ngrok.com/docs)
- [Streamlit: Remote access](https://docs.streamlit.io/develop/concepts/configuration)


---

---

## **📌 13. Tests: pytest (v9.1.1)**

### **Why pytest?**
 | **Criteria**          | **Justification** |
 |-----------------------|-------------------|
 | **Need**              | The main promise of the cloud analysis is a negative one (no real name leaves the machine). It is checked by tests rather than by a one-off look at the prompt. |
 | **No dependency on data or network** | The tests use a small synthetic table and a fake API client (`tests/test_cloud_summary.py`), so they run without Roche data, without a Mistral key and offline. |
 | **Simplicity**        | Plain functions with `assert`; `python -m pytest -q tests`. |

### **What Is Tested**
- `tests/test_pseudonymise.py`: identifying elements are replaced and restored; the same value gets the same placeholder (DeepL path).
- `tests/test_cloud_summary.py`: the request of the Smart Analysis contains no real supplier, MRP controller, purchasing group, material number or e-mail; a supplier gets the same alias in the statistics and in the comments; aliases of the streamed answer (even split across chunks) are replaced by the real names; the local prompt is unchanged.

### **Limits**
The tests do not call the real Mistral API and do not evaluate the quality of the analysis; the detection limits of section 5 (abbreviated names, person names) are not covered.

### **References**
- [pytest Documentation](https://docs.pytest.org/)

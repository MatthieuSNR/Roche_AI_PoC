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
DeepL is a **cloud service**: only the comment text is sent (no vendor, material or quantity). This is a limit to discuss with Roche; the local alternatives above remain possible.

### **References**
- [DeepL API Documentation](https://developers.deepl.com/docs)
- [langdetect (port of Google's language-detection)](https://pypi.org/project/langdetect/)

---

---

## **📌 6. AI Summary: Local LLM with LM Studio (Mistral 7B Instruct v0.3, openai client v3.26.0)**

### **Why a local LLM?**
 | **Criteria**          | **Justification** |
 |-----------------------|-------------------|
 | **Confidentiality**   | The model runs **on the laptop** (LM Studio server, `http://127.0.0.1:1234/v1`): no Roche data leaves the machine. |
 | **Reliability of figures** | **pandas computes every number** (`scripts/stats_engine.py`); the LLM only **writes** the summary from these precomputed statistics and the most frequent comments. It is instructed never to compute or invent figures. |
 | **Cost**              | No API fee, no usage limit. |
 | **Standard interface** | LM Studio exposes an **OpenAI-compatible API**: the `openai` Python client is used, so the model can be swapped without changing the code. |

### **Key Features Used in the Project** (`scripts/llm_summary.py`)
- **`chat.completions.create()`** with low temperature (0.2) for factual answers.
- **Compact prompt** (`build_facts`): only the key statistics, without indentation or duplicated figures (≈800 tokens instead of ≈1,500), and every key states its unit (`_pct` = percentage, otherwise a count) after the model turned "+75 comments" into "+75%" in a test.
- **Streaming** (`stream_summary`): the summary appears word by word in the dashboard as soon as the model starts writing.
- **Speed on the laptop** (Apple M3, 16 GB): Mistral 7B Q4_K_M writes ≈5 tokens/s when the Mac is short of memory (swap used), so a summary takes 40–60 s. Closing other applications frees memory for the model; smaller models (3–4B) are an option if speed matters more than quality.
- **Server check** (`is_server_available`) so the dashboard shows a clear message when LM Studio is not running.

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason** |
 |-----------------|----------------------|
 | Cloud LLM APIs (OpenAI, Anthropic, Azure OpenAI) | Better quality, but **confidential comments would leave the company** without an approved data agreement. |
 | Ollama | Equivalent local server; LM Studio was chosen for its graphical interface (model download, server start). |
 | Larger local models (≥ 13B) | Too slow on a laptop for an interactive dashboard. |

### **References**
- [LM Studio Documentation](https://lmstudio.ai/docs)
- [Mistral 7B Instruct v0.3](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3)


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
 | **Deployment**        | **Free hosting** on [Streamlit Cloud](https://streamlit.io/cloud).                                                                                                                                             |
 | **Industry Adoption** | Widely used by **data science teams** for internal prototypes (acquired by Snowflake in 2022).                                                                                                                      |
 | **Academic Use**      | Increasingly used in **research** for sharing interactive results (e.g., [arXiv](https://arxiv.org/)).                                                                                                         |

### **Key Features Used in the Project**
- **Widgets**: Sidebar filters (vendor, MRP controller, material, root cause, period), radio buttons, buttons.
- **One scrolling page**: an overview (ION material status tiles) followed by 7 analysis sections (comments, root causes, frequent comments, root cause details, trends, statistics, AI summary), with a menu that stays at the top of the page to jump to a section.
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
 | **Security**          | The DeepL API key is stored in a local `.env` file, **excluded from Git** by `.gitignore`. `scripts/config.py` only reads it, so the code can be pushed to GitHub without the key. |
 | **Simplicity**        | One file to edit when the key changes; `.env.example` documents the expected variables. |

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
 | `scripts/`            | **Python scripts** for the PoC (cleaning, NLP, visualization, dashboard)                          | **Modularity**: Each script has a **single responsibility**: `data_cleaning.py` (build the comments file), `translation.py` (DeepL), `stats_engine.py` (statistics), `llm_summary.py` (AI summary), `ui.py` (layout), `app.py` (dashboard). |
 | `outputs/`            | **Generated outputs** (e.g., cleaned data, visualizations, models)                              | **Reproducibility**: Outputs are saved separately to avoid overwriting and to track progress.                                                                                                                                 |
 | `venv/`               | **Virtual environment** for Python dependencies                                                | **Isolation**: Ensures dependencies (e.g., `spaCy 3.8.16`) do not conflict with other projects or system-wide Python.                                                                                              |
 | `docs/`               | **Project documentation** (e.g., this file, `project_steps.md`)                                | **Clarity**: Centralizes all documentation for easy reference by stakeholders (e.g., Roche team) and for your thesis.                                                                                              |
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



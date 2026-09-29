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
- **`pd.read_csv()`**: Load CSV files (e.g., `synthetic_data.csv`).
- **`drop_duplicates()`**: Remove duplicate rows.
- **`to_datetime()`**: Convert timestamps to datetime objects.
- **`groupby()`**: Aggregate data by categories (e.g., root causes).

### **Alternatives Considered**
 | **Alternative** | **Rejection Reason**                                                                                     |
 |-----------------|-------------------------------------------------------------------------------------------------------|
 | Polars          | Faster but **less mature** and lacks some pandas features (e.g., seamless integration with scikit-learn). |
 | Dask            | Overkill for **small-to-medium datasets** (this PoC uses <10,000 rows).                                |
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
 | **Multilingual**      | Supports **French (`fr_core_news_sm`)** and **English (`en_core_web_sm`)** out of the box.                                                                                                                           |
 | **Pre-trained Models**| Includes **pre-trained models** for NLP tasks (e.g., entity recognition, dependency parsing).                                                                                                               |
 | **Industry Adoption** | Used by **companies like Google, Microsoft, and Roche** for NLP tasks.                                                                                                                                             |
 | **Academic Use**      | Cited in **NLP research** (e.g., [ACL Anthology](https://aclanthology.org/)).                                                                                                                                     |

### **Key Features Used in the Project**
- **Tokenization**: Split text into words/tokens.
- **Lemmatization**: Reduce words to their base form (e.g., "ruptures" → "rupture").
- **Stop Word Removal**: Filter out common words (e.g., "le", "la").
- **Phrase Matching**: Extract root causes using predefined patterns (e.g., "retard fournisseur").

### **Alternatives Considered**
 | **Alternative**       | **Rejection Reason**                                                                                     |
 |-----------------------|-------------------------------------------------------------------------------------------------------|
 | NLTK                  | **Slower** and less optimized for French.                                                             |
 | Hugging Face Transformers | Overkill for **simple NLP tasks** (e.g., root cause extraction). Requires GPU for large models. |
 | Stanford NLP          | **Java-based**, not compatible with Python workflows.                                               |

### **References**
- [spaCy Official Documentation](https://spacy.io/)
- [spaCy Models: French and English](https://spacy.io/models)
- [ACL Anthology: spaCy in Research](https://aclanthology.org/)

---

---

## **📌 5. TBD**



## **📌 6. TBD **


## **📌 7. Visualization: matplotlib (v3.8.4) + seaborn (v0.13.2)**

### **Why matplotlib + seaborn?**
 | **Tool**       | **Justification**                                                                                                                                                                                                 |
 |----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | **matplotlib** | **Standard library** for basic plots (histograms, bar charts). **Integrated with pandas** (e.g., `df.plot()`).                                                                                                   |
 | **seaborn**    | **Enhanced aesthetics** for statistical plots (e.g., heatmaps, boxplots). Built on top of matplotlib.                                                                                                               |

### **Key Features Used in the Project**
- **Histograms**: Visualize root cause distribution.
- **Word Clouds**: Highlight frequent terms in comments.
- **Bar Charts**: Compare frequencies of root causes.

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
 | **Industry Adoption** | Used by **data science teams** (e.g., Roche, Google) for prototyping.                                                                                                                                               |
 | **Academic Use**      | Increasingly used in **research** for sharing interactive results (e.g., [arXiv](https://arxiv.org/)).                                                                                                         |

### **Key Features Used in the Project**
- **Widgets**: Dropdowns, sliders, and buttons for user interaction.
- **DataFrames**: Display cleaned data and results.
- **Plots**: Render matplotlib/seaborn visualizations.

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

## **📌 10. TBD**


## **📌 11. Project Structure: Why This Organization?**

### **Why This Structure?**
The project follows a **modular and scalable** structure inspired by **best practices in data science** (e.g., [Cookiecutter Data Science](https://drivendata.github.io/cookiecutter-data-science/)).
Each folder and file has a **clear purpose**, making the project **easy to maintain, debug, and extend**.
   **Folder/File**       | **Purpose**                                                                                     | **Justification**                                                                                                                                                                                                 |
 |-----------------------|-------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
 | `data/`               | **Input data** (synthetic and real)                                                            | **Separation of concerns**: Raw data is isolated from scripts and outputs to avoid confusion.                                                                                                               |
 | `scripts/`            | **Python scripts** for the PoC (cleaning, NLP, visualization, dashboard)                          | **Modularity**: Each script has a **single responsibility** (e.g., `data_cleaning.py` only cleans data). This makes the code **easier to test and reuse**.                                                                   |
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
   - **Synthetic data** allows testing without real data.

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



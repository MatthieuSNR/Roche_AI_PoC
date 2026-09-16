# Roche AI PoC: Material Availability Dashboard Optimization

## 📌 Project Overview
This project aims to develop an **AI Proof of Concept (PoC)** to extract actionable root-cause insights from unstructured planner comments in Roche's **ION Material Availability** tool. The goal is to improve transparency and decision-making for supply chain planners.

## 🛠️ Tools & Libraries
   Tool/Library   | Version   | Purpose                          |
 |----------------|-----------|----------------------------------|
 | Python         | 3.12.4    | Primary scripting language       |
 | pandas         | 2.2.3     | Data manipulation                |
 | spaCy          | 3.8.16    | NLP (text preprocessing)          |
 | scikit-learn   | 1.4.2     | Machine learning (classification)|
 | Streamlit      | 1.32.0    | Interactive dashboard             |

*(See [docs/tools_justification.md](docs/tools_justification.md) for detailed justifications.)*

## 📁 Project Structure

Roche_AI_PoC/
├── data/               # Input data (synthetic and real)
├── scripts/            # Python scripts
├── outputs/            # Results (visualizations, models)
├── docs/               # Documentation
└── requirements.txt    # Dependencies

## 🚀 How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -m spacy download fr_core_news_sm
   python -m spacy download en_core_web_sm

2. Test with synthetic data:
    python scripts/nlp_pipeline.py

3. Launch the Streamlit dashboard:
    streamlit run scripts/app.py

📊 Synthetic Data
Synthetic data is provided in data/synthetic_data.csv for testing the pipeline before receiving real data from Roche.








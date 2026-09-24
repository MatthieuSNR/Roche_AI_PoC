# Roche AI PoC: Material Availability Dashboard Optimization

## 🎯 Project Overview
This project predicts the **risk of Stock Out** for materials in Roche’s **ION Material Availability Dashboard** using:
- **Historical data** (weekly snapshots of categories, comments, root causes).
- **Supervised Machine Learning** (`RandomForest`/`XGBoost`) to predict future stock states.
- **NLP** (`TF-IDF`) to analyze **English/German comments**.

## 📊 Key Features
- **Predictive Model**: Forecasts if a material will transition to "Stock Out" in the next week.
- **Multilingual Support**: Handles comments in **English and German**.
- **Interactive Dashboard**: Streamlit app for real-time risk prediction.

## 🛠️ Tools & Libraries
   Tool/Library   | Version   | Purpose                          |
 |----------------|-----------|----------------------------------|
 | Python         | 3.12.4    | Primary scripting language       |
 | pandas         | 2.2.3     | Data manipulation                |
 | spaCy          | 3.8.16    | NLP (text preprocessing)          |
 | scikit-learn   | 1.4.2     | Machine learning (classification)|
 | Streamlit      | 1.32.0    | Interactive dashboard             |
 | joblib         | 1.3.2     | Model serialization               |


*(See [docs/tools_justification.md](docs/tools_justification.md) for detailed justifications.)*

## 📁 Project Structure

```
Roche_AI_PoC/
├── data/
│   ├── synthetic_data.csv       # Synthetic data (EN/DE)
│   └── historical_data.csv      # Real data from Roche (to request)
│
├── scripts/
│   ├── predictive_model.py      # Train the predictive model
│   └── app.py                   # Streamlit dashboard
│
├── outputs/
│   └── predictions/            # Trained model and tools
│       ├── risk_prediction_model.pkl
│       ├── tfidf_vectorizer.pkl
│       └── label_encoders.pkl
│
├── docs/
│   ├── project_steps.md        # Project steps
│   └── tools_justification.md   # Tools justification
│
└── README.md
```

## 🚀 How to Run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -m spacy download fr_core_news_sm
   python -m spacy download en_core_web_sm
   python -m spacy download de_core_news_sm

2. Test with synthetic data:
    ```bash
    python scripts/nlp_pipeline.py

2. Train the model:
    ```bash
    python scripts/predictive_model.py


3. Launch the Streamlit dashboard:
    ```bash
    streamlit run scripts/app.py

📊 Synthetic Data
Synthetic data is provided in data/synthetic_data.csv for testing the pipeline before receiving real data from Roche.








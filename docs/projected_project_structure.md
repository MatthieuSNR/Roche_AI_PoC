## 📁 (projected) Project Structure

The project is organized as follows to ensure **clarity, reproducibility, and maintainability**:

```
Roche_AI_PoC/
├── data/                       # Input data (synthetic and real)
│   ├── Snapshot_2026/          # Raw data
│   └── cleaned_comments.csv    # Cleaned data output
│
├── scripts/               # Python scripts for the PoC
│   ├── data_cleaning.py   # Data cleaning and preprocessing
│   ├── nlp_pipeline.py    # NLP processing and root cause extraction
│   ├── visualization.py   # Data visualization scripts
│   └── app.py             # Streamlit dashboard
│
├── outputs/               # Generated outputs (visualizations, models)
│   ├── root_cause_results.csv
│   └── visualizations/    # Generated plots (histograms, word clouds)
│
├── venv/                  # Virtual environment (Python dependencies)
│   ├── bin/
│   ├── lib/
│   └── pyvenv.cfg
│
├── docs/                  # Project documentation
│   ├── tools_justification.md
│   ├── project_structure.md
│   └── project_steps.md
│
├── requirements.txt       # Python dependencies list
└── README.md              # Project overview and instructions
```

### **Key Notes:**
- **`venv/`**: Contains the **isolated Python environment** with all dependencies. This ensures that the project runs consistently across different machines.
- **`data/`**: Stores input data.
- **`scripts/`**: Contains all Python scripts for data processing, NLP, and visualization.
- **`outputs/`**: Stores generated files (e.g., cleaned data, visualizations).
- **`docs/`**: Includes documentation for the thesis and project justification.


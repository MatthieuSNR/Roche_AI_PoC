import pandas as pd
import spacy
from spacy.matcher import PhraseMatcher
import os

# Get the absolute path to the project directory
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_path = os.path.join(project_dir, "data", "cleaned_data.csv")
output_path = os.path.join(project_dir, "outputs", "root_cause_results.csv")

# Load cleaned data
df = pd.read_csv(input_path)

# Load spaCy model for French
nlp = spacy.load("fr_core_news_sm")


# Function to clean text (lemmatization, remove stop words)
def clean_text(text):
    doc = nlp(text)
    return " ".join(
        [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    )


# Apply cleaning
df["Cleaned_Comment"] = df["Comment"].apply(clean_text)

# Define patterns for root causes
matcher = PhraseMatcher(nlp.vocab)
patterns = [
    nlp("retard fournisseur"),
    nlp("problème qualité"),
    nlp("rupture stock"),
    nlp("erreur commande"),
    nlp("retard logistique"),
    nlp("demande imprévue"),
]

matcher.add("ROOT_CAUSE", patterns)


# Function to extract root cause
def extract_root_cause(text):
    doc = nlp(text)
    matches = matcher(doc)
    if matches:
        return doc[matches[0][1] : matches[0][2]].text  # Return the first match
    return "Unknown"


# Apply extraction
df["Root_Cause"] = df["Comment"].apply(extract_root_cause)

# Save results
df.to_csv(output_path, index=False)

print("=== Root Cause Extraction Results ===")
print(df[["Comment", "Root_Cause"]].head())

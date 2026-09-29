import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# 1. Charger les données
df = pd.read_csv("data/Snapshot_2026/Snapshot_2026_W14_Clean.csv")

# 2. Trier par Material_ID et Timestamp
df = df.sort_values(["Material_ID", "Timestamp"])


# import glob

# 1. Lister tous les fichiers CSV dans Snapshot_2026
# csv_files = glob.glob("data/Snapshot_2026/*.csv")

# 2. Charger et combiner tous les fichiers
# dfs = []
# for file in csv_files:
#    dfs.append(pd.read_csv(file))
# df = pd.concat(dfs, ignore_index=True)

# 3. Trier par Material_ID et Timestamp
# df = df.sort_values(["Material_ID", "Timestamp"])


# 3. Créer la cible : 1 si la prochaine catégorie est "Stock Out"
df["Next_Category"] = df.groupby("Material_ID")["Category"].shift(-1)
df["Target"] = (df["Next_Category"] == "Stock Out").astype(int)
df = df.dropna(subset=["Target"])  # Supprimer les lignes sans "Next_Category"

# 4. Vectoriser les commentaires (TF-IDF)
vectorizer = TfidfVectorizer(
    max_features=100, stop_words=["the", "a", "an", "and", "or"]
)
X_comments = vectorizer.fit_transform(df["Comment"])

# 5. Encoder les catégories
from sklearn.preprocessing import LabelEncoder

le_supplier = LabelEncoder()
le_material = LabelEncoder()
le_category = LabelEncoder()
df["Supplier_Encoded"] = le_supplier.fit_transform(df["Supplier"])
df["Material_Encoded"] = le_material.fit_transform(df["Material_ID"])
df["Category_Encoded"] = le_category.fit_transform(df["Category"])

# 6. Construire la matrice de features
X = np.hstack(
    [
        df[["Supplier_Encoded", "Material_Encoded", "Category_Encoded"]].values,
        X_comments.toarray(),
    ]
)
y = df["Target"]

# 7. Entraîner le modèle
from sklearn.ensemble import RandomForestClassifier

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 8. Sauvegarder le modèle
import joblib

joblib.dump(model, "outputs/predictions/risk_prediction_model.pkl")
joblib.dump(vectorizer, "outputs/predictions/tfidf_vectorizer.pkl")
joblib.dump(
    {"Supplier": le_supplier, "Material": le_material, "Category": le_category},
    "outputs/predictions/label_encoders.pkl",
)

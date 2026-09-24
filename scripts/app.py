import streamlit as st
import pandas as pd
import numpy as np
import joblib

# Charger le modèle
model = joblib.load("outputs/predictions/risk_prediction_model.pkl")
vectorizer = joblib.load("outputs/predictions/tfidf_vectorizer.pkl")
label_encoders = joblib.load("outputs/predictions/label_encoders.pkl")

# Interface utilisateur
st.title("🔍 Roche AI PoC: Stock Out Risk Prediction")
st.markdown(
    "Predict the risk of **Stock Out** for a material based on historical patterns."
)

# Saisie des données
material_id = st.selectbox("Material ID:", ["MAT_100", "MAT_200", "MAT_300"])
supplier = st.selectbox("Supplier:", ["Supplier_X", "Supplier_Y", "Supplier_Z"])
category = st.selectbox(
    "Current Category:", ["Good Part", "Below Safety", "Potential Stock Out"]
)
comment = st.text_area("Planner Comment (EN/DE):", "Enter comment here...")

if st.button("Predict Risk"):
    # Prétraitement
    new_data = pd.DataFrame(
        {
            "Material_ID": [material_id],
            "Supplier": [supplier],
            "Category": [category],
            "Comment": [comment],
        }
    )

    # Vectoriser le commentaire
    comment_vector = vectorizer.transform([comment.lower()])

    # Encoder les catégories
    supplier_encoded = label_encoders["Supplier"].transform([supplier])[0]
    material_encoded = label_encoders["Material"].transform([material_id])[0]
    category_encoded = label_encoders["Category"].transform([category])[0]

    # Construire les features
    X_new = np.hstack(
        [
            np.array([[supplier_encoded, material_encoded, category_encoded]]),
            comment_vector.toarray(),
        ]
    )

    # Prédiction
    prediction = model.predict(X_new)[0]
    probability = model.predict_proba(X_new)[0][1]  # Probabilité de "Stock Out"

    # Afficher les résultats
    st.subheader("📊 Prediction Results")
    st.metric("Predicted Risk", "Stock Out Next Week" if prediction else "No Stock Out")
    st.metric("Probability", f"{probability * 100:.1f}%")

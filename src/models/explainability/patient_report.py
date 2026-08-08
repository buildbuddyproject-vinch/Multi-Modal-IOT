"""Per-patient SHAP explanation report, shaped to match the `prediction_history`
collection schema from docs/architecture/database_design.md (shap_values,
top_contributing_features) -- this is the payload the API/dashboard will read once
Step 7 (MongoDB) and Step 8 (FastAPI) are built."""
import numpy as np
import shap


def build_patient_explanation(shap_values: shap.Explanation, index: int, prediction_probability: float, top_n: int = 10) -> dict:
    values = shap_values.values[index]
    data = shap_values.data[index]
    names = shap_values.feature_names

    order = np.argsort(np.abs(values))[::-1][:top_n]
    top_features = [
        {"feature": names[i], "value": float(data[i]), "contribution": float(values[i])}
        for i in order
    ]

    return {
        "prediction_probability": float(prediction_probability),
        "base_value": float(shap_values.base_values[index]),
        "shap_values": {name: float(v) for name, v in zip(names, values)},
        "top_contributing_features": top_features,
        "explanation_method": "shap",
    }

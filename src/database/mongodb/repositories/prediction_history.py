"""CRUD for the `prediction_history` collection (SHAP/LIME explanation artifacts,
see src/models/explainability/patient_report.py for the payload shape this stores)."""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo.database import Database


class PredictionHistoryRepository:
    def __init__(self, db: Database):
        self.collection = db["prediction_history"]

    def create(
        self,
        prediction_id: str,
        patient_id: str,
        shap_values: dict,
        shap_plot_type: Optional[str] = None,
        top_contributing_features: Optional[list] = None,
        explanation_method: str = "shap",
    ) -> str:
        doc = {
            "prediction_id": ObjectId(prediction_id),
            "patient_id": patient_id,
            "shap_values": shap_values,
            "shap_plot_type": shap_plot_type,
            "top_contributing_features": top_contributing_features or [],
            "explanation_method": explanation_method,
            "created_at": datetime.now(timezone.utc),
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def get_by_prediction_id(self, prediction_id: str) -> Optional[dict]:
        return self.collection.find_one({"prediction_id": ObjectId(prediction_id)})

    def get_by_patient(self, patient_id: str, limit: int = 50) -> list[dict]:
        return list(self.collection.find({"patient_id": patient_id}).limit(limit))

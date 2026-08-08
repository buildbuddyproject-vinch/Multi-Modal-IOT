"""CRUD for the `predictions` collection."""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database


class PredictionRepository:
    def __init__(self, db: Database):
        self.collection = db["predictions"]

    def create(
        self,
        patient_id: str,
        sepsis_probability: float,
        predicted_label: int,
        model_version: str,
        risk_level: str,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
        inference_latency_ms: Optional[float] = None,
    ) -> str:
        doc = {
            "patient_id": patient_id,
            "window_start": window_start,
            "window_end": window_end,
            "sepsis_probability": float(sepsis_probability),
            "predicted_label": int(predicted_label),
            "model_version": model_version,
            "risk_level": risk_level,
            "inference_latency_ms": inference_latency_ms,
            "created_at": datetime.now(timezone.utc),
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def get_by_id(self, prediction_id: str) -> Optional[dict]:
        return self.collection.find_one({"_id": ObjectId(prediction_id)})

    def get_latest(self, patient_id: str) -> Optional[dict]:
        # _id is a secondary sort key: created_at has millisecond resolution, and
        # rapid successive predictions for the same patient (e.g. a fast test, or
        # a burst of simulator readings) can tie on it -- ObjectId is guaranteed
        # monotonically increasing, so it reliably breaks the tie in insertion order.
        return self.collection.find_one({"patient_id": patient_id}, sort=[("created_at", DESCENDING), ("_id", DESCENDING)])

    def get_history(self, patient_id: str, limit: int = 100) -> list[dict]:
        return list(
            self.collection.find({"patient_id": patient_id})
            .sort([("created_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )

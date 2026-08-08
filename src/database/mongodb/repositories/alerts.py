"""CRUD for the `alerts` collection."""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database


class AlertRepository:
    def __init__(self, db: Database):
        self.collection = db["alerts"]

    def create(
        self,
        patient_id: str,
        risk_level: str,
        message: str,
        prediction_id: Optional[str] = None,
        channels_dispatched: Optional[list] = None,
        dispatch_status: Optional[dict] = None,
    ) -> str:
        doc = {
            "patient_id": patient_id,
            "prediction_id": ObjectId(prediction_id) if prediction_id else None,
            "risk_level": risk_level,
            "message": message,
            "channels_dispatched": channels_dispatched or [],
            "dispatch_status": dispatch_status or {},
            "acknowledged": False,
            "acknowledged_by": None,
            "acknowledged_at": None,
            "created_at": datetime.now(timezone.utc),
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def acknowledge(self, alert_id: str, acknowledged_by: str) -> bool:
        result = self.collection.update_one(
            {"_id": ObjectId(alert_id)},
            {"$set": {
                "acknowledged": True,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.now(timezone.utc),
            }},
        )
        return result.matched_count > 0

    def list_alerts(
        self,
        patient_id: Optional[str] = None,
        patient_ids: Optional[list[str]] = None,
        acknowledged: Optional[bool] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """`patient_ids` scopes the query to a whole set at once (the caller's
        owned patients, when no single `patient_id` was requested) -- ignored
        if `patient_id` is also given, since that's already more specific."""
        query: dict = {}
        if patient_id is not None:
            query["patient_id"] = patient_id
        elif patient_ids is not None:
            query["patient_id"] = {"$in": patient_ids}
        if acknowledged is not None:
            query["acknowledged"] = acknowledged
        if risk_level is not None:
            query["risk_level"] = risk_level
        # _id as secondary sort key: see the comment in predictions.py's get_latest
        # -- created_at can tie at millisecond resolution under rapid inserts.
        return list(self.collection.find(query).sort([("created_at", DESCENDING), ("_id", DESCENDING)]).limit(limit))

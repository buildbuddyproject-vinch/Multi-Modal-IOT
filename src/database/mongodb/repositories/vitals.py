"""CRUD for the `vitals` collection -- source-agnostic per
docs/architecture/mqtt_architecture.md (simulated or real IoT sensor readings)."""
from datetime import datetime, timezone
from typing import Optional

from pymongo import DESCENDING
from pymongo.database import Database


class VitalsRepository:
    def __init__(self, db: Database):
        self.collection = db["vitals"]

    def insert_vitals(
        self,
        patient_id: str,
        timestamp: datetime,
        source: str,
        channels: dict,
        ingest_seq: Optional[int] = None,
    ) -> str:
        doc = {
            "patient_id": patient_id,
            "timestamp": timestamp,
            "source": source,
            "channels": channels,
            "ingest_seq": ingest_seq,
            "created_at": datetime.now(timezone.utc),
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def get_latest(self, patient_id: str) -> Optional[dict]:
        return self.collection.find_one({"patient_id": patient_id}, sort=[("timestamp", DESCENDING)])

    def get_history(
        self,
        patient_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[dict]:
        query: dict = {"patient_id": patient_id}
        time_filter = {}
        if start is not None:
            time_filter["$gte"] = start
        if end is not None:
            time_filter["$lte"] = end
        if time_filter:
            query["timestamp"] = time_filter
        return list(self.collection.find(query).sort("timestamp", DESCENDING).limit(limit))

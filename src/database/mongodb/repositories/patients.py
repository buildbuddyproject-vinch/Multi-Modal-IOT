"""CRUD for the `patients` collection."""
from datetime import datetime, timezone
from typing import Optional

from pymongo.database import Database


class PatientRepository:
    def __init__(self, db: Database):
        self.collection = db["patients"]

    def create(self, patient_id: str, source_dataset: str, **fields) -> str:
        now = datetime.now(timezone.utc)
        doc = {
            "patient_id": patient_id,
            "source_dataset": source_dataset,
            "current_status": fields.pop("current_status", "active"),
            "created_at": now,
            "updated_at": now,
            **fields,
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def get_by_patient_id(self, patient_id: str) -> Optional[dict]:
        return self.collection.find_one({"patient_id": patient_id})

    def update(self, patient_id: str, updates: dict) -> bool:
        updates = {**updates, "updated_at": datetime.now(timezone.utc)}
        result = self.collection.update_one({"patient_id": patient_id}, {"$set": updates})
        return result.matched_count > 0

    def list_patients(self, status: Optional[str] = None, created_by: Optional[str] = None, limit: int = 100) -> list[dict]:
        query: dict = {}
        if status:
            query["current_status"] = status
        if created_by:
            query["created_by"] = created_by
        return list(self.collection.find(query).limit(limit))

    def delete(self, patient_id: str) -> bool:
        result = self.collection.delete_one({"patient_id": patient_id})
        return result.deleted_count > 0

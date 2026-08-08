"""CRUD (append + query only -- audit logs are never updated/deleted) for the
`audit_logs` collection."""
from datetime import datetime, timezone
from typing import Optional

from pymongo import DESCENDING
from pymongo.database import Database


class AuditLogRepository:
    def __init__(self, db: Database):
        self.collection = db["audit_logs"]

    def log(
        self,
        actor: str,
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> str:
        doc = {
            "actor": actor,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc),
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def list_logs(
        self,
        action: Optional[str] = None,
        limit: int = 100,
        actor: Optional[str] = None,
        patient_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """`actor`/`patient_ids` together scope results to "things this admin
        did, plus things that happened to a patient this admin owns" -- an
        admin's audit trail is private the same way their patient list is
        (src/api/routes/patients.py)."""
        query: dict = {}
        if action:
            query["action"] = action
        if actor is not None or patient_ids is not None:
            query["$or"] = [
                {"actor": actor},
                {"details.patient_id": {"$in": patient_ids or []}},
            ]
        return list(self.collection.find(query).sort("timestamp", DESCENDING).limit(limit))

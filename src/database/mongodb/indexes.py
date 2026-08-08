"""Index definitions, matching docs/architecture/database_design.md exactly."""
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.database import Database

INDEX_SPECS: dict[str, list[IndexModel]] = {
    "patients": [
        IndexModel([("patient_id", ASCENDING)], unique=True, name="uniq_patient_id"),
        IndexModel([("current_status", ASCENDING)], name="idx_current_status"),
    ],
    "vitals": [
        IndexModel([("patient_id", ASCENDING), ("timestamp", ASCENDING)], name="idx_patient_timestamp"),
        IndexModel([("patient_id", ASCENDING), ("ingest_seq", ASCENDING)], name="idx_patient_ingest_seq"),
    ],
    "predictions": [
        IndexModel([("patient_id", ASCENDING), ("created_at", DESCENDING)], name="idx_patient_created_desc"),
    ],
    "prediction_history": [
        IndexModel([("patient_id", ASCENDING)], name="idx_patient_id"),
        IndexModel([("prediction_id", ASCENDING)], name="idx_prediction_id"),
    ],
    "alerts": [
        IndexModel([("patient_id", ASCENDING), ("created_at", DESCENDING)], name="idx_patient_created_desc"),
        IndexModel([("risk_level", ASCENDING)], name="idx_risk_level"),
        IndexModel([("acknowledged", ASCENDING)], name="idx_acknowledged"),
    ],
    "audit_logs": [
        IndexModel([("timestamp", DESCENDING)], name="idx_timestamp_desc"),
        IndexModel([("action", ASCENDING)], name="idx_action"),
    ],
    "users": [
        IndexModel([("username", ASCENDING)], unique=True, name="uniq_username"),
    ],
}


def create_all_indexes(db: Database) -> dict[str, list[str]]:
    """Creates every index in INDEX_SPECS, idempotently (safe to call on every
    startup). Returns {collection: [index names created/confirmed]}."""
    created = {}
    for collection_name, specs in INDEX_SPECS.items():
        created[collection_name] = db[collection_name].create_indexes(specs)
    return created

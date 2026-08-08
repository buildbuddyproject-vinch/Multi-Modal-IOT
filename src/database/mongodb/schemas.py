"""MongoDB $jsonSchema validators, one per collection, matching
docs/architecture/database_design.md exactly. Applied at collection-creation time
(see indexes.py / connection.init_database) so invalid documents are rejected by
MongoDB itself, not just by application code.
"""
from src.data.schema import CLINICAL_CHANNELS

CHANNEL_PROPERTIES = {channel: {"bsonType": ["double", "int", "null"]} for channel in CLINICAL_CHANNELS}

PATIENTS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["patient_id", "source_dataset"],
        "properties": {
            "patient_id": {"bsonType": "string"},
            "source_dataset": {"enum": ["physionet_2019", "mimic_iv_demo", "live"]},
            "age": {"bsonType": ["double", "int", "null"]},
            "sex": {"enum": ["M", "F", None]},
            "unit_admitted": {"bsonType": ["string", "null"]},
            "admission_time": {"bsonType": ["date", "null"]},
            "current_status": {"enum": ["active", "discharged", "deceased", None]},
            "created_at": {"bsonType": ["date", "null"]},
            "updated_at": {"bsonType": ["date", "null"]},
        },
    }
}

VITALS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["patient_id", "timestamp", "source", "channels"],
        "properties": {
            "patient_id": {"bsonType": "string"},
            "timestamp": {"bsonType": "date"},
            "source": {"enum": ["physionet_sim", "mimic_replay", "iot_sensor"]},
            "channels": {"bsonType": "object", "properties": CHANNEL_PROPERTIES},
            "ingest_seq": {"bsonType": ["int", "long", "null"]},
            "created_at": {"bsonType": ["date", "null"]},
        },
    }
}

PREDICTIONS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["patient_id", "sepsis_probability", "predicted_label", "model_version", "risk_level"],
        "properties": {
            "patient_id": {"bsonType": "string"},
            "window_start": {"bsonType": ["date", "null"]},
            "window_end": {"bsonType": ["date", "null"]},
            "sepsis_probability": {"bsonType": "double", "minimum": 0.0, "maximum": 1.0},
            "predicted_label": {"bsonType": "int", "enum": [0, 1]},
            "model_version": {"bsonType": "string"},
            "risk_level": {"enum": ["Low", "Medium", "High", "Critical"]},
            "inference_latency_ms": {"bsonType": ["double", "int", "null"]},
            "created_at": {"bsonType": ["date", "null"]},
        },
    }
}

PREDICTION_HISTORY_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["prediction_id", "patient_id", "shap_values"],
        "properties": {
            "prediction_id": {"bsonType": "objectId"},
            "patient_id": {"bsonType": "string"},
            "shap_values": {"bsonType": "object"},
            "shap_plot_type": {"enum": ["summary", "waterfall", "force", None]},
            "top_contributing_features": {"bsonType": ["array", "null"]},
            "explanation_method": {"enum": ["shap", "lime", None]},
            "created_at": {"bsonType": ["date", "null"]},
        },
    }
}

ALERTS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["patient_id", "risk_level", "message"],
        "properties": {
            "patient_id": {"bsonType": "string"},
            "prediction_id": {"bsonType": ["objectId", "null"]},
            "risk_level": {"enum": ["Low", "Medium", "High", "Critical"]},
            "message": {"bsonType": "string"},
            "channels_dispatched": {"bsonType": ["array", "null"]},
            "dispatch_status": {"bsonType": ["object", "null"]},
            "acknowledged": {"bsonType": "bool"},
            "acknowledged_by": {"bsonType": ["string", "null"]},
            "acknowledged_at": {"bsonType": ["date", "null"]},
            "created_at": {"bsonType": ["date", "null"]},
        },
    }
}

AUDIT_LOGS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["actor", "action", "timestamp"],
        "properties": {
            "actor": {"bsonType": "string"},
            "action": {"bsonType": "string"},
            "target_type": {"bsonType": ["string", "null"]},
            "target_id": {"bsonType": ["string", "null"]},
            "details": {"bsonType": ["object", "null"]},
            "timestamp": {"bsonType": "date"},
        },
    }
}

USERS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["username", "hashed_password", "role"],
        "properties": {
            "username": {"bsonType": "string"},
            "hashed_password": {"bsonType": "string"},
            "role": {"enum": ["admin", "clinician"]},
            "created_at": {"bsonType": ["date", "null"]},
            "last_login": {"bsonType": ["date", "null"]},
        },
    }
}

COLLECTION_SCHEMAS = {
    "patients": PATIENTS_SCHEMA,
    "vitals": VITALS_SCHEMA,
    "predictions": PREDICTIONS_SCHEMA,
    "prediction_history": PREDICTION_HISTORY_SCHEMA,
    "alerts": ALERTS_SCHEMA,
    "audit_logs": AUDIT_LOGS_SCHEMA,
    "users": USERS_SCHEMA,
}

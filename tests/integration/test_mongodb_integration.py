"""Integration tests against a real MongoDB (docker compose -f deployment/docker/docker-compose.yml up -d mongo).

These specifically cover what mongomock cannot: real $jsonSchema validator
enforcement and real unique-index constraint enforcement. Skipped automatically
if MongoDB isn't reachable, per docs/testing_strategy.md.
"""
from datetime import datetime, timezone

import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, WriteError

from src.database.mongodb.bootstrap import init_database
from src.database.mongodb.repositories import (
    AlertRepository,
    AuditLogRepository,
    PatientRepository,
    PredictionHistoryRepository,
    PredictionRepository,
    VitalsRepository,
)

TEST_DB_NAME = "sepsis_icu_test_integration"


def _mongo_available() -> bool:
    try:
        MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000).admin.command("ping")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB not reachable at localhost:27017 -- run `docker compose -f deployment/docker/docker-compose.yml up -d mongo`",
)


@pytest.fixture
def db():
    client = MongoClient("mongodb://localhost:27017", tz_aware=True)
    client.drop_database(TEST_DB_NAME)
    database = client[TEST_DB_NAME]
    yield database
    client.drop_database(TEST_DB_NAME)
    client.close()


def test_ping_real_mongo():
    from src.database.mongodb.connection import ping
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
    assert ping(client) is True


def test_init_database_enforces_validators_on_real_mongo(db):
    result = init_database(db)
    assert result["validator_unsupported"] == []  # real MongoDB supports $jsonSchema


def test_patients_validator_rejects_invalid_enum(db):
    init_database(db)
    with pytest.raises(WriteError):
        db["patients"].insert_one({"patient_id": "p1", "source_dataset": "not_a_real_dataset"})


def test_patients_validator_rejects_missing_required_field(db):
    init_database(db)
    with pytest.raises(WriteError):
        db["patients"].insert_one({"source_dataset": "physionet_2019"})  # missing patient_id


def test_predictions_validator_enforces_probability_range(db):
    init_database(db)
    with pytest.raises(WriteError):
        db["predictions"].insert_one({
            "patient_id": "p1", "sepsis_probability": 1.5,  # out of [0,1]
            "predicted_label": 1, "model_version": "v1", "risk_level": "High",
        })


def test_patient_id_unique_index_enforced_on_real_mongo(db):
    init_database(db)
    repo = PatientRepository(db)
    repo.create("p1", "physionet_2019")
    with pytest.raises(DuplicateKeyError):
        repo.create("p1", "physionet_2019")


def test_full_crud_round_trip_across_all_collections(db):
    """One prediction -> its SHAP explanation -> the alert it triggered -> the
    audit trail, exactly the flow Step 8's API will drive."""
    init_database(db)

    patients = PatientRepository(db)
    vitals = VitalsRepository(db)
    predictions = PredictionRepository(db)
    history = PredictionHistoryRepository(db)
    alerts = AlertRepository(db)
    audit = AuditLogRepository(db)

    patients.create("p1", "physionet_2019", age=70, sex="M")
    vitals.insert_vitals("p1", datetime.now(timezone.utc), "physionet_sim", {"HR": 110.0, "Temp": 39.2})
    pred_id = predictions.create("p1", 0.82, 1, "hybrid_v1", "Critical")
    history.create(pred_id, "p1", shap_values={"Temp": 0.12, "HR": 0.05}, explanation_method="shap")
    alert_id = alerts.create("p1", "Critical", "Sepsis risk critical", prediction_id=pred_id)
    audit.log("system", "alert_dispatched", target_type="alert", target_id=alert_id)

    assert patients.get_by_patient_id("p1")["age"] == 70
    assert vitals.get_latest("p1")["channels"]["HR"] == 110.0
    assert predictions.get_latest("p1")["risk_level"] == "Critical"
    assert history.get_by_prediction_id(pred_id)["shap_values"]["Temp"] == pytest.approx(0.12)
    assert alerts.list_alerts(patient_id="p1")[0]["message"] == "Sepsis risk critical"
    assert audit.list_logs(action="alert_dispatched")[0]["target_id"] == alert_id

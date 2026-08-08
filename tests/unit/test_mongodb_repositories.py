from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from src.database.mongodb.repositories import (
    AlertRepository,
    AuditLogRepository,
    PatientRepository,
    PredictionHistoryRepository,
    PredictionRepository,
    VitalsRepository,
)


@pytest.fixture
def db():
    return mongomock.MongoClient(tz_aware=True)["test_db"]


# --- Patients ---

def test_patient_create_and_get(db):
    repo = PatientRepository(db)
    repo.create("p1", "physionet_2019", age=65, sex="F")
    patient = repo.get_by_patient_id("p1")
    assert patient["patient_id"] == "p1"
    assert patient["age"] == 65
    assert patient["current_status"] == "active"
    assert patient["created_at"] == patient["updated_at"]


def test_patient_get_missing_returns_none(db):
    repo = PatientRepository(db)
    assert repo.get_by_patient_id("does_not_exist") is None


def test_patient_update_changes_fields_and_bumps_updated_at(db):
    repo = PatientRepository(db)
    repo.create("p1", "physionet_2019")
    original = repo.get_by_patient_id("p1")
    assert repo.update("p1", {"current_status": "discharged"}) is True
    updated = repo.get_by_patient_id("p1")
    assert updated["current_status"] == "discharged"
    assert updated["updated_at"] >= original["updated_at"]


def test_patient_update_missing_returns_false(db):
    repo = PatientRepository(db)
    assert repo.update("nope", {"current_status": "discharged"}) is False


def test_patient_list_filters_by_status(db):
    repo = PatientRepository(db)
    repo.create("p1", "physionet_2019", current_status="active")
    repo.create("p2", "physionet_2019", current_status="discharged")
    active = repo.list_patients(status="active")
    assert [p["patient_id"] for p in active] == ["p1"]


def test_patient_delete(db):
    repo = PatientRepository(db)
    repo.create("p1", "physionet_2019")
    assert repo.delete("p1") is True
    assert repo.get_by_patient_id("p1") is None
    assert repo.delete("p1") is False


# --- Vitals ---

def test_vitals_insert_and_get_latest(db):
    repo = VitalsRepository(db)
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = t1 + timedelta(hours=1)
    repo.insert_vitals("p1", t1, "physionet_sim", {"HR": 80.0})
    repo.insert_vitals("p1", t2, "physionet_sim", {"HR": 85.0})
    latest = repo.get_latest("p1")
    assert latest["timestamp"] == t2
    assert latest["channels"]["HR"] == 85.0


def test_vitals_get_history_respects_time_range(db):
    repo = VitalsRepository(db)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for h in range(5):
        repo.insert_vitals("p1", base + timedelta(hours=h), "physionet_sim", {"HR": 70.0 + h})
    history = repo.get_history("p1", start=base + timedelta(hours=1), end=base + timedelta(hours=3))
    assert len(history) == 3
    assert all(base + timedelta(hours=1) <= v["timestamp"] <= base + timedelta(hours=3) for v in history)


# --- Predictions ---

def test_prediction_create_and_get_latest(db):
    repo = PredictionRepository(db)
    repo.create("p1", 0.1, 0, "hybrid_v1", "Low")
    repo.create("p1", 0.8, 1, "hybrid_v1", "Critical")
    latest = repo.get_latest("p1")
    assert latest["risk_level"] == "Critical"
    assert latest["sepsis_probability"] == pytest.approx(0.8)


def test_prediction_get_by_id_roundtrip(db):
    repo = PredictionRepository(db)
    pred_id = repo.create("p1", 0.5, 1, "hybrid_v1", "Medium")
    fetched = repo.get_by_id(pred_id)
    assert str(fetched["_id"]) == pred_id


def test_prediction_history_returns_sorted_desc(db):
    repo = PredictionRepository(db)
    repo.create("p1", 0.1, 0, "v1", "Low")
    repo.create("p1", 0.2, 0, "v1", "Low")
    repo.create("p1", 0.3, 0, "v1", "Low")
    history = repo.get_history("p1")
    probs = [h["sepsis_probability"] for h in history]
    assert probs == sorted(probs, reverse=True)


# --- Prediction History (SHAP) ---

def test_prediction_history_create_and_fetch(db):
    pred_repo = PredictionRepository(db)
    hist_repo = PredictionHistoryRepository(db)
    pred_id = pred_repo.create("p1", 0.7, 1, "v1", "High")
    hist_repo.create(pred_id, "p1", shap_values={"Temp": 0.09}, top_contributing_features=[{"feature": "Temp", "contribution": 0.09}])
    fetched = hist_repo.get_by_prediction_id(pred_id)
    assert fetched["shap_values"]["Temp"] == pytest.approx(0.09)
    assert fetched["explanation_method"] == "shap"


def test_prediction_history_get_by_patient(db):
    pred_repo = PredictionRepository(db)
    hist_repo = PredictionHistoryRepository(db)
    pred_id = pred_repo.create("p1", 0.7, 1, "v1", "High")
    hist_repo.create(pred_id, "p1", shap_values={"Temp": 0.1})
    results = hist_repo.get_by_patient("p1")
    assert len(results) == 1


# --- Alerts ---

def test_alert_create_and_acknowledge(db):
    repo = AlertRepository(db)
    alert_id = repo.create("p1", "Critical", "Sepsis risk critical")
    alerts = repo.list_alerts(patient_id="p1")
    assert alerts[0]["acknowledged"] is False

    assert repo.acknowledge(alert_id, "dr_smith") is True
    alerts = repo.list_alerts(patient_id="p1")
    assert alerts[0]["acknowledged"] is True
    assert alerts[0]["acknowledged_by"] == "dr_smith"
    assert alerts[0]["acknowledged_at"] is not None


def test_alert_acknowledge_missing_returns_false(db):
    repo = AlertRepository(db)
    from bson import ObjectId
    assert repo.acknowledge(str(ObjectId()), "dr_smith") is False


def test_alert_list_filters_by_risk_level_and_acknowledged(db):
    repo = AlertRepository(db)
    repo.create("p1", "Low", "minor")
    id2 = repo.create("p1", "Critical", "urgent")
    repo.acknowledge(id2, "dr_smith")

    critical = repo.list_alerts(risk_level="Critical")
    assert len(critical) == 1
    unacked = repo.list_alerts(acknowledged=False)
    assert len(unacked) == 1
    assert unacked[0]["risk_level"] == "Low"


# --- Audit Logs ---

def test_audit_log_and_list(db):
    repo = AuditLogRepository(db)
    repo.log("system", "prediction_run", target_type="patient", target_id="p1", details={"probability": 0.7})
    logs = repo.list_logs()
    assert len(logs) == 1
    assert logs[0]["actor"] == "system"
    assert logs[0]["details"]["probability"] == pytest.approx(0.7)


def test_audit_log_filters_by_action(db):
    repo = AuditLogRepository(db)
    repo.log("system", "prediction_run")
    repo.log("system", "alert_dispatched")
    results = repo.list_logs(action="alert_dispatched")
    assert len(results) == 1
    assert results[0]["action"] == "alert_dispatched"

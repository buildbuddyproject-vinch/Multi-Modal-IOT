from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from bson import ObjectId

import src.alerts.alert_engine as alert_engine_module
from src.alerts.alert_engine import AlertEngine
from src.database.mongodb.repositories import AlertRepository, AuditLogRepository, VitalsRepository


@pytest.fixture
def engine(monkeypatch):
    # Deterministic, network-free stand-in for the MQTT dispatch -- whether a
    # broker happens to be reachable while running unit tests is irrelevant to
    # what's being tested here (threshold/cooldown/escalation decisions).
    monkeypatch.setattr(alert_engine_module, "publish_alert_mqtt", lambda *a, **k: "sent")
    db = mongomock.MongoClient(tz_aware=True)["test_db"]
    return AlertEngine(AlertRepository(db), AuditLogRepository(db), VitalsRepository(db))


def _prediction(risk_level="Critical", probability=0.8):
    return {"id": str(ObjectId()), "sepsis_probability": probability, "risk_level": risk_level}


def test_low_risk_prediction_raises_no_alert(engine):
    assert engine.evaluate_and_dispatch("p1", _prediction(risk_level="Low", probability=0.02)) is None
    assert engine.alert_repo.list_alerts() == []


def test_medium_risk_prediction_raises_no_alert_by_default(engine):
    assert engine.evaluate_and_dispatch("p1", _prediction(risk_level="Medium", probability=0.15)) is None


def test_high_risk_prediction_raises_an_alert(engine):
    alert_id = engine.evaluate_and_dispatch("p1", _prediction(risk_level="High", probability=0.3))
    assert alert_id is not None
    alerts = engine.alert_repo.list_alerts()
    assert len(alerts) == 1
    assert alerts[0]["risk_level"] == "High"
    assert alerts[0]["dispatch_status"] == {"telegram": "skipped", "email": "skipped", "mqtt": "sent"}
    assert alerts[0]["channels_dispatched"] == ["mqtt"]


def test_alert_dispatch_writes_an_audit_log_entry(engine):
    alert_id = engine.evaluate_and_dispatch("p1", _prediction(risk_level="Critical"))
    logs = engine.audit_repo.list_logs(action="alert_dispatched")
    assert len(logs) == 1
    assert logs[0]["target_id"] == alert_id
    assert logs[0]["details"]["patient_id"] == "p1"


def test_second_alert_at_same_risk_within_cooldown_is_suppressed(engine):
    first = engine.evaluate_and_dispatch("p1", _prediction(risk_level="High"))
    assert first is not None
    second = engine.evaluate_and_dispatch("p1", _prediction(risk_level="High"))
    assert second is None
    assert len(engine.alert_repo.list_alerts()) == 1


def test_escalating_risk_bypasses_cooldown(engine):
    first = engine.evaluate_and_dispatch("p1", _prediction(risk_level="High"))
    second = engine.evaluate_and_dispatch("p1", _prediction(risk_level="Critical"))
    assert first is not None
    assert second is not None
    assert second != first
    assert len(engine.alert_repo.list_alerts()) == 2


def test_de_escalating_risk_within_cooldown_is_still_suppressed(engine):
    engine.evaluate_and_dispatch("p1", _prediction(risk_level="Critical"))
    suppressed = engine.evaluate_and_dispatch("p1", _prediction(risk_level="High"))
    assert suppressed is None


def test_alert_after_cooldown_expires_is_not_suppressed(engine):
    engine.alert_repo.create("p1", "High", "earlier alert")
    # backdate the alert past the cooldown window
    doc = engine.alert_repo.collection.find_one({"patient_id": "p1"})
    engine.alert_repo.collection.update_one(
        {"_id": doc["_id"]}, {"$set": {"created_at": datetime.now(timezone.utc) - timedelta(minutes=999)}}
    )
    alert_id = engine.evaluate_and_dispatch("p1", _prediction(risk_level="High"))
    assert alert_id is not None
    assert len(engine.alert_repo.list_alerts()) == 2


def test_different_patients_do_not_share_cooldown(engine):
    engine.evaluate_and_dispatch("p1", _prediction(risk_level="Critical"))
    alert_id = engine.evaluate_and_dispatch("p2", _prediction(risk_level="Critical"))
    assert alert_id is not None


def test_alert_message_explains_why_using_the_patients_latest_vitals(engine):
    engine.vitals_repo.insert_vitals(
        "p1", datetime.now(timezone.utc), "iot_sensor",
        {"HR": 118.0, "Temp": 39.1, "SBP": 82.0},
    )
    alert_id = engine.evaluate_and_dispatch("p1", _prediction(risk_level="Critical"))
    message = engine.alert_repo.collection.find_one({"_id": ObjectId(alert_id)})["message"]
    assert "Elevated Heart rate (118" in message
    assert "Elevated Temperature (39" in message
    assert "Low Systolic BP (82" in message


def test_alert_message_falls_back_when_no_vital_crosses_a_threshold(engine):
    engine.vitals_repo.insert_vitals("p1", datetime.now(timezone.utc), "iot_sensor", {"HR": 80.0, "Temp": 37.0})
    alert_id = engine.evaluate_and_dispatch("p1", _prediction(risk_level="Critical"))
    message = engine.alert_repo.collection.find_one({"_id": ObjectId(alert_id)})["message"]
    assert "SHAP explanation" in message


def test_alert_message_falls_back_when_patient_has_no_vitals_yet(engine):
    alert_id = engine.evaluate_and_dispatch("p1", _prediction(risk_level="Critical"))
    message = engine.alert_repo.collection.find_one({"_id": ObjectId(alert_id)})["message"]
    assert "SHAP explanation" in message

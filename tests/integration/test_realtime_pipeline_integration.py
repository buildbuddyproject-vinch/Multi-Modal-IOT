"""End-to-end MQTT smoke test for Step 11 against REAL running infrastructure:
    docker compose -f deployment/docker/docker-compose.yml --profile mqtt up -d mosquitto
    uvicorn src.api.main:app --host 127.0.0.1 --port 8000
    python scripts/run_realtime_pipeline.py --owner-username admin --owner-password "SepsisIcu2026!"

Publishes real MQTT messages (exactly what the Step 11 simulator or Phase 2
ESP32 firmware would send) and verifies the already-running pipeline process
picks them up: vitals land in the API, and once 8 readings have arrived for a
patient, a real prediction (from the real trained model) appears too."""
import time

import httpx
import paho.mqtt.publish as mqtt_publish
import pytest

from src.config.settings import get_settings
from src.mqtt.client import vitals_topic

API_BASE_URL = "http://127.0.0.1:8000"
TEST_PATIENT_ID = "mqtt_it_test_patient"
WINDOW_SIZE = 8
# Matches the --owner-username/--owner-password the live pipeline process
# (scripts/run_realtime_pipeline.py) is started with in this project -- every
# patient it auto-provisions is owned by this account (per-account privacy
# model, src/api/routes/patients.py), so reading its data back requires the
# same identity.
PIPELINE_OWNER_USERNAME = "admin"
PIPELINE_OWNER_PASSWORD = "SepsisIcu2026!"


def _api_available() -> bool:
    try:
        return httpx.get(f"{API_BASE_URL}/health", timeout=2.0).json().get("mongo_connected") is True
    except Exception:
        return False


def _mqtt_available() -> bool:
    settings = get_settings()
    try:
        mqtt_publish.single(
            "icu/_health_check/vitals", payload="{}",
            hostname=settings.mqtt_broker_host, port=settings.mqtt_broker_port,
        )
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_api_available() and _mqtt_available()),
    reason="requires a live API, Mosquitto broker, and a running `python scripts/run_realtime_pipeline.py` consumer",
)


def _publish_reading(hr: float, seq: int) -> None:
    from datetime import datetime, timezone
    settings = get_settings()
    mqtt_publish.single(
        vitals_topic(TEST_PATIENT_ID),
        payload=(
            '{"patient_id": "%s", "timestamp": "%s", "source": "physionet_sim", '
            '"channels": {"HR": %.1f, "O2Sat": 97.0, "Temp": 37.0}}'
        ) % (TEST_PATIENT_ID, datetime.now(timezone.utc).isoformat(), hr),
        qos=1, hostname=settings.mqtt_broker_host, port=settings.mqtt_broker_port,
    )


def _wait_until(predicate, timeout_seconds=20, interval=0.5):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _owner_client() -> httpx.Client:
    token = httpx.post(f"{API_BASE_URL}/auth/login", json={
        "username": PIPELINE_OWNER_USERNAME, "password": PIPELINE_OWNER_PASSWORD,
    }).json()["access_token"]
    return httpx.Client(base_url=API_BASE_URL, headers={"Authorization": f"Bearer {token}"})


def test_published_vitals_are_ingested_by_the_running_pipeline():
    client = _owner_client()
    _publish_reading(hr=88.0, seq=1)

    def vitals_arrived():
        resp = client.get(f"/vitals/{TEST_PATIENT_ID}/latest")
        return resp.status_code == 200 and resp.json()["channels"]["HR"] == 88.0

    assert _wait_until(vitals_arrived), "pipeline did not ingest the published vitals reading in time"

    patient_resp = client.get(f"/patients/{TEST_PATIENT_ID}")
    assert patient_resp.status_code == 200
    assert patient_resp.json()["current_status"] == "active"


def test_a_full_window_of_readings_produces_a_real_model_prediction():
    client = _owner_client()
    for i in range(WINDOW_SIZE):
        _publish_reading(hr=80.0 + i, seq=i)
        time.sleep(0.2)

    def prediction_arrived():
        resp = client.get(f"/predictions/{TEST_PATIENT_ID}/latest")
        return resp.status_code == 200

    assert _wait_until(prediction_arrived, timeout_seconds=30), "pipeline did not produce a prediction in time"
    prediction = client.get(f"/predictions/{TEST_PATIENT_ID}/latest").json()
    assert 0.0 <= prediction["sepsis_probability"] <= 1.0
    assert prediction["risk_level"] in ("Low", "Medium", "High", "Critical")
    assert prediction["model_version"] == "hybrid_cnn_bilstm_transformer_v1"

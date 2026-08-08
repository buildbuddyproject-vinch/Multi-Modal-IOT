import json

import httpx
import mongomock
import numpy as np
import pytest

from src.data.schema import CLINICAL_CHANNELS
from src.services.realtime_pipeline import (
    MAX_PAYLOAD_BYTES,
    RealtimePipeline,
    impute_and_normalize_reading,
    validate_vitals_message,
)

# Real usage always supplies stats for every one of the 34 clinical channels
# (loaded from metadata.json) -- match that shape here so a channel like SBP
# isn't accidentally missing and masking a real bug behind a fixture gap.
MEAN = {c: 50.0 for c in CLINICAL_CHANNELS} | {"HR": 84.0, "O2Sat": 97.0, "Temp": 37.0}
STD = {c: 10.0 for c in CLINICAL_CHANNELS} | {"HR": 17.0, "O2Sat": 3.0, "Temp": 0.7}
MEDIANS = {c: 50.0 for c in CLINICAL_CHANNELS} | {"HR": 83.0, "O2Sat": 98.0, "Temp": 36.8}


def _valid_payload(**overrides) -> dict:
    payload = {
        "patient_id": "p1", "timestamp": "2026-08-05T10:00:00Z", "source": "iot_sensor",
        "channels": {"HR": 90.0, "O2Sat": None},
    }
    payload.update(overrides)
    return payload


# --- validate_vitals_message ---

def test_valid_message_passes():
    payload = _valid_payload()
    assert validate_vitals_message(json.dumps(payload).encode(), payload) is None


def test_rejects_oversized_payload():
    payload = _valid_payload()
    raw = b"x" * (MAX_PAYLOAD_BYTES + 1)
    assert "exceeds" in validate_vitals_message(raw, payload)


def test_rejects_invalid_json():
    assert validate_vitals_message(b"not json", None) == "payload is not valid JSON"


def test_rejects_missing_patient_id():
    payload = _valid_payload(patient_id="")
    assert "patient_id" in validate_vitals_message(json.dumps(payload).encode(), payload)


def test_rejects_missing_timestamp():
    payload = _valid_payload(timestamp="")
    assert "timestamp" in validate_vitals_message(json.dumps(payload).encode(), payload)


def test_rejects_unknown_source():
    payload = _valid_payload(source="wearable_prototype")
    assert "source" in validate_vitals_message(json.dumps(payload).encode(), payload)


def test_rejects_non_numeric_channel_value():
    payload = _valid_payload(channels={"HR": "high"})
    assert "HR" in validate_vitals_message(json.dumps(payload).encode(), payload)


def test_rejects_channels_not_an_object():
    payload = _valid_payload(channels="none")
    assert "channels" in validate_vitals_message(json.dumps(payload).encode(), payload)


# --- impute_and_normalize_reading ---

def test_impute_uses_observed_value_when_present():
    vector, last_known = impute_and_normalize_reading({"HR": 101.0, "O2Sat": None, "Temp": None}, {}, MEDIANS, MEAN, STD)
    idx = {"HR": 0, "O2Sat": 1, "Temp": 2}
    assert vector[idx["HR"]] == pytest.approx((101.0 - 84.0) / 17.0)
    assert last_known["HR"] == 101.0


def test_impute_forward_fills_from_last_known_when_missing():
    _, last_known = impute_and_normalize_reading({"HR": 100.0}, {}, MEDIANS, MEAN, STD)
    vector, last_known2 = impute_and_normalize_reading({"HR": None}, last_known, MEDIANS, MEAN, STD)
    idx = 0  # HR is first in CLINICAL_CHANNELS
    assert vector[idx] == pytest.approx((100.0 - 84.0) / 17.0)
    assert last_known2["HR"] == 100.0


def test_impute_falls_back_to_median_when_never_observed():
    vector, _ = impute_and_normalize_reading({}, {}, MEDIANS, MEAN, STD)
    idx = 0
    assert vector[idx] == pytest.approx((MEDIANS["HR"] - MEAN["HR"]) / STD["HR"])


# --- RealtimePipeline ---

class _FakeTensor:
    """Mimics the one bit of the TF tensor interface the pipeline actually
    uses (model(X) is called directly, not via .predict(), per the same
    reasoning as src/models/explainability/shap_explainer.py's make_predict_fn)."""
    def __init__(self, array):
        self._array = array

    def numpy(self):
        return self._array


class FakeModel:
    def __call__(self, X, training=False):
        return _FakeTensor(np.array([[0.9]], dtype=np.float32))


class RecordingMqttClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0):
        self.published.append((topic, payload, qos))


@pytest.fixture
def pipeline():
    db = mongomock.MongoClient(tz_aware=True)["test_db"]

    def handler(request):
        if request.url.path == "/patients" and request.method == "POST":
            return httpx.Response(409, json={"detail": "already exists"})  # idempotent re-provisioning, see _ensure_patient_exists
        if request.url.path == "/vitals":
            return httpx.Response(201, json={})
        if request.url.path == "/predictions":
            return httpx.Response(201, json={
                "id": "pred1", "sepsis_probability": 0.9, "risk_level": "Critical", "created_at": "2026-08-05T10:00:00Z",
            })
        return httpx.Response(404)

    p = RealtimePipeline(
        db, FakeModel(), MEAN, STD, MEDIANS, "http://testserver",
        transport=httpx.MockTransport(handler), mqtt_client=RecordingMqttClient(),
    )
    return p


def test_handle_message_rejects_and_audits_malformed_payload(pipeline):
    pipeline.handle_message("icu/p1/vitals", b"not json")
    logs = pipeline.audit_repo.list_logs(action="vitals_rejected")
    assert len(logs) == 1


def test_handle_message_forwards_valid_vitals_and_buffers_window(pipeline):
    payload = _valid_payload()
    pipeline.handle_message("icu/p1/vitals", json.dumps(payload).encode())
    assert len(pipeline._windows["p1"]) == 1
    assert pipeline.audit_repo.list_logs(action="vitals_rejected") == []


def test_window_fills_and_triggers_prediction_and_mqtt_publish(pipeline):
    for _ in range(8):
        pipeline.handle_message("icu/p1/vitals", json.dumps(_valid_payload()).encode())

    assert len(pipeline._windows["p1"]) == 8
    assert len(pipeline.mqtt.published) == 1
    topic, payload, qos = pipeline.mqtt.published[0]
    assert topic == "icu/p1/prediction"
    body = json.loads(payload)
    assert body["risk_level"] == "Critical"


def test_ensure_patient_exists_reattempts_provisioning_every_message_not_just_once():
    """Regression test: an earlier version cached patient_id after the first
    successful provisioning and never tried again, which meant a patient
    record deleted out from under a long-running pipeline was never recreated.
    _ensure_patient_exists must retry the (idempotent) POST every time."""
    db = mongomock.MongoClient(tz_aware=True)["test_db"]
    post_patient_calls = []

    def handler(request):
        if request.url.path == "/patients" and request.method == "POST":
            post_patient_calls.append(request)
            return httpx.Response(409, json={"detail": "already exists"})
        if request.url.path == "/vitals":
            return httpx.Response(201, json={})
        return httpx.Response(404)

    p = RealtimePipeline(
        db, FakeModel(), MEAN, STD, MEDIANS, "http://testserver",
        transport=httpx.MockTransport(handler), mqtt_client=RecordingMqttClient(),
    )
    for _ in range(3):
        p.handle_message("icu/p1/vitals", json.dumps(_valid_payload()).encode())

    assert len(post_patient_calls) == 3

"""Step 11 "Ingestion Service" + "Prediction Service"
(docs/architecture/mqtt_architecture.md, database_design.md): the backend-side
counterpart to the untrusted simulator. Subscribes to icu/+/vitals, validates
each message against the documented payload contract, forwards well-formed
readings to the real API (POST /vitals), maintains a per-patient sliding
window, and once a window is full runs the actual trained model and forwards
the result to POST /predictions -- which already handles authoritative
risk-level computation, audit logging, and alerting (Step 10). Nothing here
cares whether the message originated from the Phase 1 simulator or Phase 2
ESP32 firmware; both speak the identical MQTT contract.
"""
import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional, get_args

import httpx
import numpy as np

from src.api.schemas.common import VitalsSource
from src.data.schema import CLINICAL_CHANNELS
from src.database.mongodb.repositories import AuditLogRepository
from src.mqtt.client import HEARTBEAT_TOPIC, VITALS_TOPIC_FILTER, build_client, connect, prediction_topic

logger = logging.getLogger(__name__)

MAX_PAYLOAD_BYTES = 4096
VALID_SOURCES = set(get_args(VitalsSource))
WINDOW_SIZE = 8
MODEL_VERSION = "hybrid_cnn_bilstm_transformer_v1"


def validate_vitals_message(raw_bytes: bytes, payload: Optional[dict]) -> Optional[str]:
    """Enforces docs/architecture/mqtt_architecture.md §3's four rules.
    Returns None if the message is well-formed, else a rejection reason."""
    if len(raw_bytes) > MAX_PAYLOAD_BYTES:
        return f"payload exceeds {MAX_PAYLOAD_BYTES} bytes"
    if payload is None:
        return "payload is not valid JSON"
    if not payload.get("patient_id"):
        return "missing required field: patient_id"
    if not payload.get("timestamp"):
        return "missing required field: timestamp"
    if payload.get("source") not in VALID_SOURCES:
        return f"source must be one of {sorted(VALID_SOURCES)}"
    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return "channels must be an object"
    for name, value in channels.items():
        if value is not None and not isinstance(value, (int, float)):
            return f"channel '{name}' must be a number or null, got {type(value).__name__}"
    return None


def impute_and_normalize_reading(
    channels: dict, last_known: dict[str, float], medians: dict[str, float], mean: dict[str, float], std: dict[str, float]
) -> tuple[np.ndarray, dict[str, float]]:
    """Forward-fill (last known reading carries forward) then fall back to the
    train-set median for a channel never yet observed for this patient --
    identical imputation philosophy to the batch pipeline's
    src/data/preprocessing/cleaning.py, adapted to a streaming, one-row-at-a-time
    setting. Returns the z-score-normalized channel vector plus the updated
    last-known-values cache."""
    updated_last_known = dict(last_known)
    values = np.empty(len(CLINICAL_CHANNELS), dtype=np.float32)
    for i, channel in enumerate(CLINICAL_CHANNELS):
        reading = channels.get(channel)
        if reading is not None:
            updated_last_known[channel] = reading
        raw_value = updated_last_known.get(channel, medians.get(channel, 0.0))
        values[i] = (raw_value - mean[channel]) / std[channel]
    return values, updated_last_known


class RealtimePipeline:
    def __init__(
        self, db, model, mean: dict, std: dict, medians: dict, api_base_url: str,
        transport: Optional[httpx.BaseTransport] = None, mqtt_client=None, owner_token: Optional[str] = None,
    ):
        """`owner_token` is the JWT of whichever account "owns" every patient
        this pipeline auto-provisions (src/api/routes/patients.py's
        per-account privacy model) -- see scripts/run_realtime_pipeline.py's
        --owner-username/--owner-password, which obtains it once at startup."""
        self.audit_repo = AuditLogRepository(db)
        self.model = model
        self.mean, self.std, self.medians = mean, std, medians
        headers = {"Authorization": f"Bearer {owner_token}"} if owner_token else {}
        self.api = httpx.Client(base_url=api_base_url, headers=headers, timeout=10.0, transport=transport)
        self.mqtt = mqtt_client if mqtt_client is not None else build_client(client_id="realtime_pipeline")
        self._last_known: dict[str, dict[str, float]] = {}
        self._windows: dict[str, deque] = {}

    def close(self) -> None:
        self.api.close()

    def handle_message(self, topic: str, raw_bytes: bytes) -> None:
        try:
            payload = json.loads(raw_bytes)
        except json.JSONDecodeError:
            payload = None

        reason = validate_vitals_message(raw_bytes, payload)
        if reason is not None:
            logger.warning("Rejected MQTT message on %s: %s", topic, reason)
            self.audit_repo.log(actor="ingestion_service", action="vitals_rejected", target_type="mqtt_message",
                                 details={"topic": topic, "reason": reason})
            return

        patient_id = payload["patient_id"]
        self._ensure_patient_exists(patient_id)

        resp = self.api.post("/vitals", json=payload)
        if resp.status_code >= 400:
            logger.warning("API rejected vitals for %s: %s", patient_id, resp.text)
            self.audit_repo.log(actor="ingestion_service", action="vitals_rejected", target_type="patient",
                                 target_id=patient_id, details={"reason": resp.text})
            return

        self._buffer_and_maybe_predict(patient_id, payload)

    def _ensure_patient_exists(self, patient_id: str) -> None:
        """Always attempts the (idempotent) POST rather than caching "already
        seen" patient_ids -- a GET-then-cache approach would go stale and stop
        recreating the patient record if it were ever removed from Mongo out
        from under a long-running pipeline process; a 409 here is simply the
        expected outcome for every message after the first."""
        resp = self.api.post("/patients", json={"patient_id": patient_id, "source_dataset": "live", "current_status": "active"})
        if resp.status_code not in (201, 409):
            logger.warning("Could not provision patient %s: %s", patient_id, resp.text)

    def _buffer_and_maybe_predict(self, patient_id: str, payload: dict) -> None:
        last_known = self._last_known.get(patient_id, {})
        vector, last_known = impute_and_normalize_reading(payload["channels"], last_known, self.medians, self.mean, self.std)
        self._last_known[patient_id] = last_known

        window = self._windows.setdefault(patient_id, deque(maxlen=WINDOW_SIZE))
        window.append(vector)
        if len(window) < WINDOW_SIZE:
            return

        window_array = np.stack(window, axis=0)[None, ...].astype(np.float32)
        probability = float(self.model(window_array, training=False).numpy()[0, 0])

        resp = self.api.post("/predictions", json={
            "patient_id": patient_id, "sepsis_probability": probability, "model_version": MODEL_VERSION,
            "window_end": payload["timestamp"],
        })
        if resp.status_code >= 400:
            logger.warning("Failed to record prediction for %s: %s", patient_id, resp.text)
            return

        prediction = resp.json()
        self.mqtt.publish(prediction_topic(patient_id), json.dumps({
            "sepsis_probability": prediction["sepsis_probability"],
            "risk_level": prediction["risk_level"],
            "timestamp": prediction["created_at"],
        }), qos=1)

    def run(self, heartbeat_seconds: float = 30.0) -> None:
        """Runs the MQTT network loop on a background thread (loop_start) so the
        main thread is free to publish a periodic heartbeat -- loop_forever()
        would block it entirely."""
        connect(self.mqtt)
        self.mqtt.on_message = lambda client, userdata, msg: self.handle_message(msg.topic, msg.payload)
        self.mqtt.subscribe(VITALS_TOPIC_FILTER, qos=1)
        self.mqtt.loop_start()
        try:
            while True:
                self.publish_heartbeat()
                time.sleep(heartbeat_seconds)
        finally:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()

    def publish_heartbeat(self) -> None:
        self.mqtt.publish(HEARTBEAT_TOPIC, json.dumps({
            "service": "realtime_pipeline", "status": "alive", "timestamp": datetime.now(timezone.utc).isoformat(),
        }), qos=0)

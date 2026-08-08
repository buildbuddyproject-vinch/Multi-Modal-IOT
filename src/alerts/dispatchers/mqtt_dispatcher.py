"""Publishes an alert to icu/{patient_id}/alert (docs/architecture/mqtt_architecture.md
§2) alongside Telegram/email -- a channel any Phase 2 bedside display or future
direct-subscriber dashboard panel can listen to without touching the REST API."""
from datetime import datetime, timezone

from src.mqtt.client import alert_topic, publish_json


def publish_alert_mqtt(patient_id: str, risk_level: str, message: str) -> str:
    """Returns 'sent' or 'failed' -- there's no "not configured" skip state
    here the way there is for Telegram/email, since the broker host/port
    always have a default; if it's unreachable that's a 'failed' dispatch."""
    payload = {
        "risk_level": risk_level, "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ok = publish_json(alert_topic(patient_id), payload, qos=1)
    return "sent" if ok else "failed"

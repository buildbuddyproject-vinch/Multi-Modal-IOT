"""Shared paho-mqtt connection helpers. Both the untrusted simulator
(src/data/simulation) and the backend-side ingestion/prediction pipeline
(src/services/realtime_pipeline.py) connect to the same broker using this
module -- it only knows about connection mechanics (host/port/credentials),
never about ICU semantics, so it's equally usable by Phase 2 firmware-adjacent
tooling.
"""
import json
import logging
from typing import Optional

import paho.mqtt.client as mqtt
import paho.mqtt.publish as mqtt_publish

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

QOS_AT_LEAST_ONCE = 1
QOS_AT_MOST_ONCE = 0


def build_client(client_id: str) -> mqtt.Client:
    """A persistent client for a long-running publisher/subscriber process.
    Caller is responsible for connect()/loop_start()/disconnect()."""
    settings = get_settings()
    client = mqtt.Client(client_id=client_id, clean_session=True)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password or None)
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    return client


def connect(client: mqtt.Client) -> None:
    settings = get_settings()
    client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, keepalive=30)


def publish_json(topic: str, payload: dict, qos: int = QOS_AT_MOST_ONCE) -> bool:
    """One-shot publish (connect, publish, disconnect) for low-frequency callers
    like the alert engine, which shouldn't have to manage a persistent MQTT
    connection just to send an occasional message."""
    settings = get_settings()
    auth = {"username": settings.mqtt_username, "password": settings.mqtt_password or None} if settings.mqtt_username else None
    try:
        mqtt_publish.single(
            topic, payload=json.dumps(payload), qos=qos,
            hostname=settings.mqtt_broker_host, port=settings.mqtt_broker_port, auth=auth,
        )
        return True
    except Exception:
        logger.exception("MQTT publish to %s failed", topic)
        return False


def vitals_topic(patient_id: str) -> str:
    return f"icu/{patient_id}/vitals"


def status_topic(patient_id: str) -> str:
    return f"icu/{patient_id}/status"


def prediction_topic(patient_id: str) -> str:
    return f"icu/{patient_id}/prediction"


def alert_topic(patient_id: str) -> str:
    return f"icu/{patient_id}/alert"


HEARTBEAT_TOPIC = "system/heartbeat"
VITALS_TOPIC_FILTER = "icu/+/vitals"

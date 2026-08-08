import json

import paho.mqtt.publish as mqtt_publish

from src.mqtt.client import (
    HEARTBEAT_TOPIC,
    VITALS_TOPIC_FILTER,
    alert_topic,
    prediction_topic,
    publish_json,
    status_topic,
    vitals_topic,
)


def test_topic_helpers_match_the_documented_contract():
    assert vitals_topic("p1") == "icu/p1/vitals"
    assert status_topic("p1") == "icu/p1/status"
    assert prediction_topic("p1") == "icu/p1/prediction"
    assert alert_topic("p1") == "icu/p1/alert"
    assert HEARTBEAT_TOPIC == "system/heartbeat"
    assert VITALS_TOPIC_FILTER == "icu/+/vitals"


def test_publish_json_serializes_payload_and_returns_true_on_success(monkeypatch):
    captured = {}

    def fake_single(topic, payload, qos, hostname, port, auth):
        captured.update(topic=topic, payload=payload, qos=qos, hostname=hostname, port=port)

    monkeypatch.setattr(mqtt_publish, "single", fake_single)
    ok = publish_json("icu/p1/vitals", {"HR": 88.0}, qos=1)

    assert ok is True
    assert captured["topic"] == "icu/p1/vitals"
    assert json.loads(captured["payload"]) == {"HR": 88.0}
    assert captured["qos"] == 1


def test_publish_json_returns_false_on_broker_error(monkeypatch):
    def fake_single(*args, **kwargs):
        raise ConnectionRefusedError("no broker")

    monkeypatch.setattr(mqtt_publish, "single", fake_single)
    assert publish_json("icu/p1/vitals", {"HR": 88.0}) is False

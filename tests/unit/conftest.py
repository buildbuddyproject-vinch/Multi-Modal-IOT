import pytest

import src.alerts.alert_engine as alert_engine_module


@pytest.fixture(autouse=True)
def _no_real_mqtt_alert_dispatch(monkeypatch):
    """Unit tests must not depend on a Mosquitto broker being reachable --
    that's what tests/integration/test_api_integration.py is for. Telegram/
    email already no-op ('skipped') without real credentials in a fresh test
    env, but MQTT always attempts a connection, so it's the one channel that
    needs an explicit stand-in here."""
    monkeypatch.setattr(alert_engine_module, "publish_alert_mqtt", lambda *a, **k: "skipped")

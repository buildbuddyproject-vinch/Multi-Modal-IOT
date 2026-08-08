import httpx
import pytest

from src.alerts.dispatchers.email_dispatcher import send_email_alert
from src.alerts.dispatchers.mqtt_dispatcher import publish_alert_mqtt
from src.alerts.dispatchers.telegram_dispatcher import send_telegram_alert
from src.config.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_telegram_skipped_when_not_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    assert send_telegram_alert("test") == "skipped"


def test_telegram_sent_on_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    def fake_post(url, json, timeout):
        assert "fake-token" in url
        assert json["chat_id"] == "12345"
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    assert send_telegram_alert("Critical sepsis risk for p1") == "sent"


def test_telegram_failed_on_http_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    def fake_post(url, json, timeout):
        return httpx.Response(401, json={"ok": False}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    assert send_telegram_alert("test") == "failed"


def test_telegram_failed_on_network_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")

    def fake_post(url, json, timeout):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", fake_post)
    assert send_telegram_alert("test") == "failed"


def test_email_skipped_when_not_configured(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("ALERT_EMAIL_TO", "")
    assert send_email_alert("subject", "body") == "skipped"


def test_email_sent_on_success(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("ALERT_EMAIL_FROM", "bot@example.com")
    monkeypatch.setenv("ALERT_EMAIL_TO", "oncall@example.com")

    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            calls.append(("starttls",))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, msg):
            calls.append(("send", msg["To"], msg["Subject"]))

    import smtplib

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    assert send_email_alert("Critical Alert", "Patient p1 is Critical") == "sent"
    assert ("send", "oncall@example.com", "Critical Alert") in calls
    assert ("login", "bot@example.com", "secret") in calls


def test_email_failed_on_smtp_exception(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("ALERT_EMAIL_TO", "oncall@example.com")

    import smtplib

    class FailingSMTP:
        def __init__(self, host, port, timeout):
            raise smtplib.SMTPConnectError(421, "cannot connect")

    monkeypatch.setattr(smtplib, "SMTP", FailingSMTP)
    assert send_email_alert("subject", "body") == "failed"


def test_mqtt_alert_sent_publishes_to_the_correct_topic(monkeypatch):
    import src.alerts.dispatchers.mqtt_dispatcher as mqtt_dispatcher_module

    captured = {}

    def fake_publish_json(topic, payload, qos):
        captured.update(topic=topic, payload=payload, qos=qos)
        return True

    monkeypatch.setattr(mqtt_dispatcher_module, "publish_json", fake_publish_json)
    assert publish_alert_mqtt("p1", "Critical", "Sepsis risk critical") == "sent"
    assert captured["topic"] == "icu/p1/alert"
    assert captured["payload"]["risk_level"] == "Critical"
    assert captured["qos"] == 1


def test_mqtt_alert_failed_when_publish_fails(monkeypatch):
    import src.alerts.dispatchers.mqtt_dispatcher as mqtt_dispatcher_module

    monkeypatch.setattr(mqtt_dispatcher_module, "publish_json", lambda *a, **k: False)
    assert publish_alert_mqtt("p1", "Critical", "test") == "failed"

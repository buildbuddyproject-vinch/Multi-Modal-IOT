from dashboard.components.alert_toast import build_alert_toast


def _alert(**overrides) -> dict:
    alert = {
        "id": "a1", "patient_id": "p1", "risk_level": "Critical",
        "message": "Critical sepsis risk detected", "created_at": "2026-08-05T10:00:00+00:00",
    }
    alert.update(overrides)
    return alert


def test_critical_alert_renders_toast_with_critical_styling():
    toast = build_alert_toast(_alert(risk_level="Critical"))
    assert type(toast).__name__ == "Toast"
    assert toast.icon == "danger"
    assert "icu-alert-toast-critical" in toast.class_name
    rendered = str(toast)
    assert "p1" in rendered
    assert "Critical sepsis risk detected" in rendered


def test_high_alert_renders_toast_with_warning_styling():
    toast = build_alert_toast(_alert(risk_level="High"))
    assert toast.icon == "warning"
    assert "icu-alert-toast-high" in toast.class_name


def test_toast_auto_hides_and_is_dismissable():
    toast = build_alert_toast(_alert())
    assert toast.duration and toast.duration > 0
    assert toast.dismissable is True
    assert toast.is_open is True

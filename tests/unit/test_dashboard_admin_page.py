import dashboard.app  # noqa: F401 -- must instantiate the Dash app (use_pages=True) before importing a page module
from dashboard.pages.admin import _build_audit_log_table


def test_empty_audit_log_shows_placeholder():
    table = _build_audit_log_table([])
    assert type(table).__name__ == "Alert"


def test_audit_log_table_renders_rows():
    logs = [
        {"action": "login", "actor": "admin", "target_type": "user", "target_id": "admin", "timestamp": "2026-08-05T10:00:00+00:00"},
        {"action": "alert_dispatched", "actor": "system", "target_type": "alert", "target_id": "abc123", "timestamp": "2026-08-05T10:05:00+00:00"},
    ]
    table = _build_audit_log_table(logs)
    assert type(table).__name__ == "Table"
    rendered = str(table)
    assert "login" in rendered
    assert "alert_dispatched" in rendered
    assert "admin" in rendered

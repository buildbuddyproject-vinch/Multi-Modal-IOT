from src.api.security import hash_password
from src.database.mongodb.repositories import UserRepository


def _login(client, test_db, username="admin", password="adminpass123", role="admin"):
    UserRepository(test_db).create(username, hash_password(password), role)
    return client.post("/auth/login", json={"username": username, "password": password}).json()["access_token"]


def test_audit_logs_requires_authentication(client):
    assert client.get("/audit-logs").status_code == 401


def test_audit_logs_requires_admin_role(client, test_db):
    token = _login(client, test_db, username="nurse", role="clinician")
    resp = client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_sees_login_audit_entry(client, test_db):
    token = _login(client, test_db)
    resp = client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    actions = [log["action"] for log in resp.json()]
    assert "login" in actions


def test_audit_logs_filter_by_action(client, test_db):
    token = _login(client, test_db)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=headers)
    client.post("/predictions", json={"patient_id": "p1", "sepsis_probability": 0.9, "model_version": "v1"}, headers=headers)

    resp = client.get("/audit-logs", params={"action": "prediction_run"}, headers=headers)
    assert resp.status_code == 200
    actions = {log["action"] for log in resp.json()}
    assert actions == {"prediction_run"}


def test_prediction_and_alert_actions_are_logged(client, test_db):
    token = _login(client, test_db)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=headers)
    client.post("/predictions", json={"patient_id": "p1", "sepsis_probability": 0.9, "model_version": "v1"}, headers=headers)

    actions = {log["action"] for log in client.get("/audit-logs", headers=headers).json()}
    assert "prediction_run" in actions
    assert "alert_dispatched" in actions


def test_admin_does_not_see_another_admins_prediction_activity(client, test_db):
    """Audit visibility follows the same per-account privacy as everything
    else -- one admin's actions on their own patients aren't visible to a
    second, unrelated admin account."""
    token_a = _login(client, test_db, username="admin_a")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=headers_a)
    client.post("/predictions", json={"patient_id": "p1", "sepsis_probability": 0.9, "model_version": "v1"}, headers=headers_a)

    token_b = _login(client, test_db, username="admin_b")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    actions_b = {log["action"] for log in client.get("/audit-logs", headers=headers_b).json()}
    assert "prediction_run" not in actions_b
    assert "alert_dispatched" not in actions_b
    # admin_b's own login is still visible to them
    assert "login" in actions_b

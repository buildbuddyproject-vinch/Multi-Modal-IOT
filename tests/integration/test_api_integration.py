"""API integration tests against a real MongoDB (docker compose -f
deployment/docker/docker-compose.yml up -d mongo). Covers what mongomock-backed
unit tests cannot: real $jsonSchema validator + unique-index enforcement reaching
all the way through the API, and a full end-to-end flow across every router."""
import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from src.api.dependencies import get_db
from src.api.main import app
from src.api.security import hash_password
from src.database.mongodb.bootstrap import init_database
from src.database.mongodb.repositories import UserRepository

TEST_DB_NAME = "sepsis_icu_test_api_integration"


def _mongo_available() -> bool:
    try:
        MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000).admin.command("ping")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB not reachable at localhost:27017 -- run `docker compose -f deployment/docker/docker-compose.yml up -d mongo`",
)


@pytest.fixture
def client():
    mongo_client = MongoClient("mongodb://localhost:27017", tz_aware=True)
    mongo_client.drop_database(TEST_DB_NAME)
    db = mongo_client[TEST_DB_NAME]
    init_database(db)

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    mongo_client.drop_database(TEST_DB_NAME)
    mongo_client.close()


def _admin_auth_header(client) -> dict:
    UserRepository(app.dependency_overrides[get_db]()).create("admin_it", hash_password("adminpass123"), "admin")
    token = client.post("/auth/login", json={"username": "admin_it", "password": "adminpass123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check_reports_real_mongo_connected(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["mongo_connected"] is True


def test_duplicate_patient_id_rejected_via_real_unique_index(client):
    headers = _admin_auth_header(client)
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=headers)
    resp = client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=headers)
    assert resp.status_code == 409


def test_full_flow_across_every_router(client):
    """Patient -> vitals -> prediction -> SHAP explanation -> alert -> ack,
    exactly the pipeline Steps 9-11 will drive against this API."""
    headers = _admin_auth_header(client)
    assert client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019", "age": 70}, headers=headers).status_code == 201

    from datetime import datetime, timezone
    vitals_resp = client.post("/vitals", json={
        "patient_id": "p1", "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "iot_sensor", "channels": {"HR": 115.0, "Temp": 39.3},
    }, headers=headers)
    assert vitals_resp.status_code == 201

    pred_resp = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.85, "model_version": "hybrid_v1",
    }, headers=headers)
    assert pred_resp.status_code == 201
    prediction_id = pred_resp.json()["id"]
    assert pred_resp.json()["risk_level"] == "Critical"

    shap_resp = client.post("/shap", json={
        "prediction_id": prediction_id, "patient_id": "p1",
        "shap_values": {"Temp": 0.15, "HR": 0.08},
        "shap_plot_type": "waterfall",
    }, headers=headers)
    assert shap_resp.status_code == 201

    # a Critical prediction runs through the Step 10 alert engine automatically --
    # no manual POST /alerts needed for the normal pipeline
    alerts = client.get("/alerts", params={"patient_id": "p1"}, headers=headers).json()
    assert len(alerts) == 1
    assert alerts[0]["risk_level"] == "Critical"
    alert_id = alerts[0]["id"]

    ack_resp = client.patch(f"/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "dr_smith"}, headers=headers)
    assert ack_resp.status_code == 200

    # verify everything is retrievable and consistent end-to-end
    assert client.get("/patients/p1", headers=headers).json()["age"] == 70
    assert client.get("/vitals/p1/latest", headers=headers).json()["channels"]["HR"] == 115.0
    assert client.get("/predictions/p1/latest", headers=headers).json()["risk_level"] == "Critical"
    assert client.get(f"/shap/prediction/{prediction_id}", headers=headers).json()["shap_values"]["Temp"] == pytest.approx(0.15)
    alerts = client.get("/alerts", params={"patient_id": "p1"}, headers=headers).json()
    assert alerts[0]["acknowledged"] is True

    audit_actions = {log["action"] for log in client.get("/audit-logs", headers=headers).json()}
    assert {"prediction_run", "alert_dispatched", "alert_acknowledged"} <= audit_actions

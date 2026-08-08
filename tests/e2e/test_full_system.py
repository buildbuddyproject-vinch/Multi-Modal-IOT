"""Step 12 capstone: the entire clinical workflow, start to finish, against the
REAL running stack -- no mocks anywhere in this file. Requires:
    docker compose -f deployment/docker/docker-compose.yml up -d mongo
    uvicorn src.api.main:app --host 127.0.0.1 --port 8000
    python scripts/run_dashboard.py

Deliberately does NOT depend on scripts/run_realtime_pipeline.py or
scripts/run_realtime_simulator.py being up in another terminal -- that MQTT
path is already covered end-to-end by
tests/integration/test_realtime_pipeline_integration.py. This test instead
loads the real trained model directly (the same way scripts/seed_dashboard_demo_data.py
does) so it's self-contained and deterministic: login -> patient -> vitals ->
a REAL model prediction on a REAL held-out test-set window -> a REAL SHAP
explanation -> an automatic alert (Step 10's engine) -> acknowledge -> audit
trail -> the dashboard (Step 9) actually rendering all of it.
"""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
import pytest

API_BASE_URL = "http://127.0.0.1:8000"
DASHBOARD_BASE_URL = "http://127.0.0.1:8050"
WINDOW_SIZE = 8


def _api_available() -> bool:
    try:
        return httpx.get(f"{API_BASE_URL}/health", timeout=2.0).json().get("mongo_connected") is True
    except Exception:
        return False


def _dashboard_available() -> bool:
    try:
        return httpx.get(f"{DASHBOARD_BASE_URL}/login", timeout=2.0).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_api_available() and _dashboard_available()),
    reason="requires a live API (uvicorn src.api.main:app) and dashboard (scripts/run_dashboard.py) on localhost",
)


@pytest.fixture(scope="module")
def high_confidence_septic_window():
    """A real held-out PhysioNet test-set window with SepsisLabel=1, picked for
    the highest model-predicted probability -- guarantees this test's alert
    step is deterministic rather than depending on luck."""
    import keras

    import src.models.architectures.transformer_block  # noqa: F401
    import src.models.training.losses  # noqa: F401
    from src.config.settings import get_settings

    settings = get_settings()
    model = keras.models.load_model(settings.resolve_path("./models") / "saved" / "final_model.keras", compile=False)
    with np.load(settings.processed_dir / "physionet2019" / "test.npz") as data:
        X_test, y_test = data["X"], data["y"]

    positive_idx = np.where(y_test == 1)[0]
    probabilities = model(X_test[positive_idx], training=False).numpy().ravel()
    best = positive_idx[np.argmax(probabilities)]
    return model, X_test[best]


@pytest.fixture(scope="module")
def admin_credentials():
    from src.api.security import hash_password
    from src.database.mongodb.connection import get_client, get_database
    from src.database.mongodb.repositories import UserRepository

    username = f"e2e_admin_{uuid.uuid4().hex[:8]}"
    password = "E2eTestPass123!"
    db = get_database(get_client())
    UserRepository(db).create(username, hash_password(password), "admin")
    return username, password


@pytest.fixture(scope="module")
def admin_token(admin_credentials):
    username, password = admin_credentials
    resp = httpx.post(f"{API_BASE_URL}/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


def test_full_clinical_workflow_end_to_end(high_confidence_septic_window, admin_token):
    model, window = high_confidence_septic_window
    probability = float(model(window[None, ...], training=False).numpy()[0, 0])
    assert probability > 0.2, "expected the highest-confidence real septic window to score as elevated risk"

    patient_id = f"e2e_patient_{uuid.uuid4().hex[:8]}"
    client = httpx.Client(base_url=API_BASE_URL, headers={"Authorization": f"Bearer {admin_token}"})

    # --- 1. Patient admission ---
    resp = client.post("/patients", json={"patient_id": patient_id, "source_dataset": "physionet_2019", "age": 66, "sex": "M"})
    assert resp.status_code == 201

    # --- 2. Vitals ingestion (8 hourly readings, as a real device/simulator would send) ---
    start = datetime.now(timezone.utc) - timedelta(hours=WINDOW_SIZE)
    for hour in range(WINDOW_SIZE):
        resp = client.post("/vitals", json={
            "patient_id": patient_id, "timestamp": (start + timedelta(hours=hour)).isoformat(),
            "source": "physionet_sim", "channels": {"HR": 100.0 + hour, "Temp": 38.0 + hour * 0.1, "Resp": 22.0},
        })
        assert resp.status_code == 201
    assert len(client.get(f"/vitals/{patient_id}/history").json()) == WINDOW_SIZE

    # --- 3. Prediction (real model output; risk_level/predicted_label computed server-side, Step 10) ---
    resp = client.post("/predictions", json={
        "patient_id": patient_id, "sepsis_probability": probability, "model_version": "hybrid_cnn_bilstm_transformer_v1",
    })
    assert resp.status_code == 201
    prediction = resp.json()
    assert prediction["risk_level"] in ("High", "Critical")
    prediction_id = prediction["id"]

    # --- 4. SHAP explanation (real explainer, Step 6) ---
    from src.data.schema import CLINICAL_CHANNELS
    from src.models.explainability.patient_report import build_patient_explanation
    from src.models.explainability.shap_explainer import build_explainer, compute_shap_values

    background = np.tile(window.mean(axis=0), (10, WINDOW_SIZE, 1))
    explainer = build_explainer(model, background, WINDOW_SIZE, len(CLINICAL_CHANNELS), channel_names=CLINICAL_CHANNELS)
    shap_result = compute_shap_values(explainer, window[None, ...], max_evals=100)
    explanation = build_patient_explanation(shap_result, index=0, prediction_probability=probability)

    resp = client.post("/shap", json={
        "prediction_id": prediction_id, "patient_id": patient_id,
        "shap_values": explanation["shap_values"], "top_contributing_features": explanation["top_contributing_features"],
    })
    assert resp.status_code == 201

    # --- 5. Alert engine fired automatically (Step 10) ---
    alerts = client.get("/alerts", params={"patient_id": patient_id}).json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["risk_level"] == prediction["risk_level"]
    assert alert["acknowledged"] is False
    assert "mqtt" in alert["dispatch_status"]  # Step 11's dispatcher, always attempted

    # --- 6. Acknowledge ---
    resp = client.patch(f"/alerts/{alert['id']}/acknowledge", json={"acknowledged_by": "dr_e2e_test"})
    assert resp.status_code == 200
    assert client.get("/alerts", params={"patient_id": patient_id}).json()[0]["acknowledged"] is True

    # --- 7. Audit trail covers every step above ---
    audit_actions = {log["action"] for log in client.get("/audit-logs", params={"limit": 500}).json()}
    assert {"login", "prediction_run", "alert_dispatched", "alert_acknowledged"} <= audit_actions

    # --- 8. The dashboard (Step 9) actually renders what this test just created ---
    from dashboard import auth
    from dashboard.app import server
    from dashboard.pages.patient_detail import load_patient_detail
    from dashboard.pages.patients import load_patients

    with server.test_request_context("/"):
        auth.log_in(admin_token, "e2e", "admin")

        patients_table = load_patients(1)
        assert patient_id in str(patients_table)

        header, vitals_tab, prediction_tab, shap_tab = load_patient_detail(1, patient_id)
        assert patient_id in str(header)
        assert type(vitals_tab).__name__ == "Graph"
        assert type(prediction_tab).__name__ == "Graph"
        assert type(shap_tab).__name__ == "Div"  # real SHAP explanation rendered, not the "no explanation" placeholder

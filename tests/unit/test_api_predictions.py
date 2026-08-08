def _create_patient(client, headers, patient_id="p1"):
    client.post("/patients", json={"patient_id": patient_id, "source_dataset": "physionet_2019"}, headers=headers)


def test_create_prediction_and_get_latest(client, admin_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.82, "model_version": "hybrid_v1",
    }, headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["sepsis_probability"] == 0.82
    assert "id" in body

    resp = client.get("/predictions/p1/latest", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["risk_level"] == "Critical"


def test_create_prediction_for_unowned_patient_returns_404(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.82, "model_version": "hybrid_v1",
    }, headers=clinician_headers)
    assert resp.status_code == 404


def test_risk_level_and_predicted_label_are_computed_server_side_from_probability(client, admin_headers):
    """predicted_label/risk_level aren't client input (Step 10) -- they're
    derived from sepsis_probability so the alert engine can trust them."""
    _create_patient(client, admin_headers)
    resp = client.post("/predictions", json={"patient_id": "p1", "sepsis_probability": 0.02, "model_version": "v1"}, headers=admin_headers)
    body = resp.json()
    assert body["risk_level"] == "Low"
    assert body["predicted_label"] == 0


def test_client_supplied_risk_level_and_predicted_label_are_ignored(client, admin_headers):
    """A caller sending stale/incorrect risk_level or predicted_label (e.g. an
    older client) must not be able to override the server's computation."""
    _create_patient(client, admin_headers)
    resp = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.02, "model_version": "v1",
        "risk_level": "Critical", "predicted_label": 1,
    }, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["risk_level"] == "Low"
    assert resp.json()["predicted_label"] == 0


def test_create_prediction_rejects_out_of_range_probability(client, admin_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 1.5, "model_version": "hybrid_v1",
    }, headers=admin_headers)
    assert resp.status_code == 422


def test_get_latest_prediction_missing_patient_returns_404(client, admin_headers):
    resp = client.get("/predictions/nope/latest", headers=admin_headers)
    assert resp.status_code == 404


def test_prediction_history_sorted_most_recent_first(client, admin_headers):
    _create_patient(client, admin_headers)
    for prob in (0.01, 0.02, 0.03):
        client.post("/predictions", json={"patient_id": "p1", "sepsis_probability": prob, "model_version": "v1"}, headers=admin_headers)
    resp = client.get("/predictions/p1/history", headers=admin_headers)
    assert resp.status_code == 200
    probs = [p["sepsis_probability"] for p in resp.json()]
    assert probs == [0.03, 0.02, 0.01]


def test_high_risk_prediction_automatically_raises_an_alert(client, admin_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/predictions", json={"patient_id": "p1", "sepsis_probability": 0.9, "model_version": "v1"}, headers=admin_headers)
    assert resp.status_code == 201

    alerts = client.get("/alerts", params={"patient_id": "p1"}, headers=admin_headers).json()
    assert len(alerts) == 1
    assert alerts[0]["risk_level"] == "Critical"


def test_low_risk_prediction_does_not_raise_an_alert(client, admin_headers):
    _create_patient(client, admin_headers)
    client.post("/predictions", json={"patient_id": "p1", "sepsis_probability": 0.01, "model_version": "v1"}, headers=admin_headers)
    alerts = client.get("/alerts", params={"patient_id": "p1"}, headers=admin_headers).json()
    assert alerts == []

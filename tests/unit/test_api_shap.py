def _create_patient(client, headers, patient_id="p1"):
    client.post("/patients", json={"patient_id": patient_id, "source_dataset": "physionet_2019"}, headers=headers)


def test_create_and_get_shap_explanation_by_prediction(client, admin_headers):
    _create_patient(client, admin_headers)
    pred_id = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.7, "predicted_label": 1,
        "model_version": "v1", "risk_level": "High",
    }, headers=admin_headers).json()["id"]

    resp = client.post("/shap", json={
        "prediction_id": pred_id, "patient_id": "p1",
        "shap_values": {"Temp": 0.09, "HR": 0.02},
        "shap_plot_type": "waterfall",
        "top_contributing_features": [{"feature": "Temp", "value": 2.6, "contribution": 0.09}],
    }, headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["shap_values"]["Temp"] == 0.09
    assert body["top_contributing_features"][0]["feature"] == "Temp"

    resp = client.get(f"/shap/prediction/{pred_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["explanation_method"] == "shap"


def test_create_shap_explanation_for_unowned_patient_returns_404(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers)
    pred_id = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.7, "model_version": "v1",
    }, headers=admin_headers).json()["id"]

    resp = client.post("/shap", json={"prediction_id": pred_id, "patient_id": "p1", "shap_values": {"Temp": 0.1}}, headers=clinician_headers)
    assert resp.status_code == 404


def test_get_explanation_missing_prediction_returns_404(client, admin_headers):
    from bson import ObjectId
    resp = client.get(f"/shap/prediction/{ObjectId()}", headers=admin_headers)
    assert resp.status_code == 404


def test_get_explanation_for_another_accounts_patient_returns_404(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers)
    pred_id = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.7, "model_version": "v1",
    }, headers=admin_headers).json()["id"]
    client.post("/shap", json={"prediction_id": pred_id, "patient_id": "p1", "shap_values": {"Temp": 0.1}}, headers=admin_headers)

    resp = client.get(f"/shap/prediction/{pred_id}", headers=clinician_headers)
    assert resp.status_code == 404


def test_get_explanations_by_patient(client, admin_headers):
    _create_patient(client, admin_headers)
    pred_id = client.post("/predictions", json={
        "patient_id": "p1", "sepsis_probability": 0.7, "model_version": "v1",
    }, headers=admin_headers).json()["id"]
    client.post("/shap", json={"prediction_id": pred_id, "patient_id": "p1", "shap_values": {"Temp": 0.1}}, headers=admin_headers)

    resp = client.get("/shap/patient/p1", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_shap_explanation_malformed_prediction_id_returns_400(client, admin_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/shap", json={"prediction_id": "not-an-object-id", "patient_id": "p1", "shap_values": {"Temp": 0.1}}, headers=admin_headers)
    assert resp.status_code == 400

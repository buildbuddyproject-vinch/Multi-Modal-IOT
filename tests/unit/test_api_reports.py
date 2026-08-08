def _seed_patient_with_history(client, headers, patient_id="p1"):
    client.post("/patients", json={"patient_id": patient_id, "source_dataset": "physionet_2019", "age": 66, "sex": "M"}, headers=headers)
    client.post("/vitals", json={
        "patient_id": patient_id, "timestamp": "2026-08-05T10:00:00+00:00",
        "source": "physionet_sim", "channels": {"HR": 110.0, "Temp": 38.9},
    }, headers=headers)
    pred_id = client.post("/predictions", json={
        "patient_id": patient_id, "sepsis_probability": 0.83, "model_version": "hybrid_cnn_bilstm_transformer_v1",
    }, headers=headers).json()["id"]
    client.post("/shap", json={
        "prediction_id": pred_id, "patient_id": patient_id,
        "shap_values": {"Lactate": 0.31}, "top_contributing_features": [{"feature": "Lactate", "value": 4.2, "contribution": 0.31}],
    }, headers=headers)
    return pred_id


def test_get_patient_report_returns_pdf(client, admin_headers):
    _seed_patient_with_history(client, admin_headers)

    resp = client.get("/patients/p1/report", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "p1_sepsis_report.pdf" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")


def test_get_patient_report_missing_patient_returns_404(client, admin_headers):
    resp = client.get("/patients/does-not-exist/report", headers=admin_headers)
    assert resp.status_code == 404


def test_get_patient_report_for_another_accounts_patient_returns_404(client, admin_headers, clinician_headers):
    _seed_patient_with_history(client, admin_headers)
    resp = client.get("/patients/p1/report", headers=clinician_headers)
    assert resp.status_code == 404


def test_get_patient_report_works_with_no_predictions_yet(client, admin_headers):
    client.post("/patients", json={"patient_id": "p2", "source_dataset": "live"}, headers=admin_headers)

    resp = client.get("/patients/p2/report", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")

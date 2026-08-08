def _create_patient(client, headers, patient_id="p1"):
    client.post("/patients", json={"patient_id": patient_id, "source_dataset": "physionet_2019"}, headers=headers)


def test_create_and_list_alert(client, admin_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/alerts", json={"patient_id": "p1", "risk_level": "Critical", "message": "Sepsis risk critical"}, headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["acknowledged"] is False

    resp = client.get("/alerts", params={"patient_id": "p1"}, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_alert_for_unowned_patient_returns_404(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/alerts", json={"patient_id": "p1", "risk_level": "Critical", "message": "x"}, headers=clinician_headers)
    assert resp.status_code == 404


def test_create_alert_rejects_invalid_risk_level(client, admin_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/alerts", json={"patient_id": "p1", "risk_level": "Super Bad", "message": "x"}, headers=admin_headers)
    assert resp.status_code == 422


def test_acknowledge_alert(client, admin_headers):
    _create_patient(client, admin_headers)
    alert_id = client.post("/alerts", json={"patient_id": "p1", "risk_level": "High", "message": "elevated risk"}, headers=admin_headers).json()["id"]
    resp = client.patch(f"/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "dr_smith"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["acknowledged"] is True

    alerts = client.get("/alerts", params={"patient_id": "p1"}, headers=admin_headers).json()
    assert alerts[0]["acknowledged"] is True
    assert alerts[0]["acknowledged_by"] == "dr_smith"


def test_cannot_acknowledge_another_accounts_alert(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers)
    alert_id = client.post("/alerts", json={"patient_id": "p1", "risk_level": "High", "message": "elevated risk"}, headers=admin_headers).json()["id"]
    resp = client.patch(f"/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "dr_other"}, headers=clinician_headers)
    assert resp.status_code == 404


def test_acknowledge_missing_alert_returns_404(client, admin_headers):
    from bson import ObjectId
    resp = client.patch(f"/alerts/{ObjectId()}/acknowledge", json={"acknowledged_by": "dr_smith"}, headers=admin_headers)
    assert resp.status_code == 404


def test_acknowledge_malformed_alert_id_returns_400(client, admin_headers):
    resp = client.patch("/alerts/not-a-valid-object-id/acknowledge", json={"acknowledged_by": "dr_smith"}, headers=admin_headers)
    assert resp.status_code == 400


def test_list_alerts_filters_by_risk_level_and_acknowledged(client, admin_headers):
    _create_patient(client, admin_headers)
    client.post("/alerts", json={"patient_id": "p1", "risk_level": "Low", "message": "minor"}, headers=admin_headers)
    alert2 = client.post("/alerts", json={"patient_id": "p1", "risk_level": "Critical", "message": "urgent"}, headers=admin_headers).json()["id"]
    client.patch(f"/alerts/{alert2}/acknowledge", json={"acknowledged_by": "dr_smith"}, headers=admin_headers)

    critical = client.get("/alerts", params={"risk_level": "Critical"}, headers=admin_headers).json()
    assert len(critical) == 1
    unacked = client.get("/alerts", params={"acknowledged": False}, headers=admin_headers).json()
    assert len(unacked) == 1
    assert unacked[0]["risk_level"] == "Low"


def test_list_alerts_without_patient_filter_is_still_scoped_to_owned_patients(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers, "admin_p1")
    _create_patient(client, clinician_headers, "clinician_p1")
    client.post("/alerts", json={"patient_id": "admin_p1", "risk_level": "Critical", "message": "x"}, headers=admin_headers)
    client.post("/alerts", json={"patient_id": "clinician_p1", "risk_level": "Critical", "message": "y"}, headers=clinician_headers)

    admin_alerts = client.get("/alerts", headers=admin_headers).json()
    clinician_alerts = client.get("/alerts", headers=clinician_headers).json()
    assert [a["patient_id"] for a in admin_alerts] == ["admin_p1"]
    assert [a["patient_id"] for a in clinician_alerts] == ["clinician_p1"]

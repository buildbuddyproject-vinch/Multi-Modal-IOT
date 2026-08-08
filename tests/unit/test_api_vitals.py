from datetime import datetime, timedelta, timezone


def _create_patient(client, headers, patient_id="p1"):
    client.post("/patients", json={"patient_id": patient_id, "source_dataset": "physionet_2019"}, headers=headers)


def test_ingest_and_get_latest_vitals(client, admin_headers):
    _create_patient(client, admin_headers)
    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post("/vitals", json={
        "patient_id": "p1", "timestamp": ts, "source": "physionet_sim",
        "channels": {"HR": 88.0, "Temp": 37.1},
    }, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["channels"]["HR"] == 88.0

    resp = client.get("/vitals/p1/latest", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["channels"]["Temp"] == 37.1


def test_ingest_vitals_requires_authentication(client, admin_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/vitals", json={
        "patient_id": "p1", "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "physionet_sim", "channels": {"HR": 88.0},
    })
    assert resp.status_code == 401


def test_ingest_vitals_for_unowned_patient_returns_404(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers)
    resp = client.post("/vitals", json={
        "patient_id": "p1", "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "physionet_sim", "channels": {"HR": 88.0},
    }, headers=clinician_headers)
    assert resp.status_code == 404


def test_ingest_vitals_rejects_unknown_channel(client, admin_headers):
    _create_patient(client, admin_headers)
    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post("/vitals", json={
        "patient_id": "p1", "timestamp": ts, "source": "physionet_sim",
        "channels": {"NotARealChannel": 1.0},
    }, headers=admin_headers)
    assert resp.status_code == 422


def test_ingest_vitals_rejects_invalid_source(client, admin_headers):
    _create_patient(client, admin_headers)
    ts = datetime.now(timezone.utc).isoformat()
    resp = client.post("/vitals", json={
        "patient_id": "p1", "timestamp": ts, "source": "not_a_real_source",
        "channels": {"HR": 80.0},
    }, headers=admin_headers)
    assert resp.status_code == 422


def test_get_latest_vitals_missing_patient_returns_404(client, admin_headers):
    resp = client.get("/vitals/nope/latest", headers=admin_headers)
    assert resp.status_code == 404


def test_get_vitals_for_another_accounts_patient_returns_404(client, admin_headers, clinician_headers):
    _create_patient(client, admin_headers)
    resp = client.get("/vitals/p1/latest", headers=clinician_headers)
    assert resp.status_code == 404


def test_vitals_history_respects_time_range(client, admin_headers):
    _create_patient(client, admin_headers)
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for h in range(5):
        client.post("/vitals", json={
            "patient_id": "p1", "timestamp": (base + timedelta(hours=h)).isoformat(),
            "source": "physionet_sim", "channels": {"HR": 70.0 + h},
        }, headers=admin_headers)
    resp = client.get("/vitals/p1/history", params={
        "start": (base + timedelta(hours=1)).isoformat(),
        "end": (base + timedelta(hours=3)).isoformat(),
    }, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3

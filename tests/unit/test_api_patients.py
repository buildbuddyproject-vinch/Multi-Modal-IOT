def test_create_and_get_patient(client, admin_headers):
    resp = client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019", "age": 65, "sex": "F"}, headers=admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["patient_id"] == "p1"
    assert body["current_status"] == "active"
    assert body["created_by"] == "test_admin"

    resp = client.get("/patients/p1", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["age"] == 65


def test_create_patient_requires_authentication(client):
    resp = client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"})
    assert resp.status_code == 401


def test_create_patient_duplicate_returns_409(client, admin_headers):
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    assert resp.status_code == 409


def test_create_patient_invalid_source_dataset_returns_422(client, admin_headers):
    resp = client.post("/patients", json={"patient_id": "p1", "source_dataset": "not_a_real_source"}, headers=admin_headers)
    assert resp.status_code == 422


def test_create_patient_invalid_age_returns_422(client, admin_headers):
    resp = client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019", "age": 999}, headers=admin_headers)
    assert resp.status_code == 422


def test_get_missing_patient_returns_404(client, admin_headers):
    resp = client.get("/patients/does_not_exist", headers=admin_headers)
    assert resp.status_code == 404


def test_list_patients_filters_by_status(client, admin_headers):
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019", "current_status": "active"}, headers=admin_headers)
    client.post("/patients", json={"patient_id": "p2", "source_dataset": "physionet_2019", "current_status": "discharged"}, headers=admin_headers)
    resp = client.get("/patients", params={"status_filter": "active"}, headers=admin_headers)
    assert resp.status_code == 200
    ids = [p["patient_id"] for p in resp.json()]
    assert ids == ["p1"]


def test_update_patient(client, admin_headers):
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.patch("/patients/p1", json={"current_status": "discharged"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["current_status"] == "discharged"


def test_update_missing_patient_returns_404(client, admin_headers):
    resp = client.patch("/patients/nope", json={"current_status": "discharged"}, headers=admin_headers)
    assert resp.status_code == 404


def test_update_with_no_fields_returns_400(client, admin_headers):
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.patch("/patients/p1", json={}, headers=admin_headers)
    assert resp.status_code == 400


def test_delete_patient(client, admin_headers):
    client.post("/patients", json={"patient_id": "p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.delete("/patients/p1", headers=admin_headers)
    assert resp.status_code == 204
    assert client.get("/patients/p1", headers=admin_headers).status_code == 404


def test_delete_missing_patient_returns_404(client, admin_headers):
    resp = client.delete("/patients/nope", headers=admin_headers)
    assert resp.status_code == 404


# --- per-account ownership isolation (the whole point of this schema) ---

def test_list_patients_only_shows_the_callers_own_patients(client, admin_headers, clinician_headers):
    client.post("/patients", json={"patient_id": "admin_p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    client.post("/patients", json={"patient_id": "clinician_p1", "source_dataset": "physionet_2019"}, headers=clinician_headers)

    admin_ids = [p["patient_id"] for p in client.get("/patients", headers=admin_headers).json()]
    clinician_ids = [p["patient_id"] for p in client.get("/patients", headers=clinician_headers).json()]
    assert admin_ids == ["admin_p1"]
    assert clinician_ids == ["clinician_p1"]


def test_get_another_accounts_patient_returns_404_not_403(client, admin_headers, clinician_headers):
    client.post("/patients", json={"patient_id": "admin_p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.get("/patients/admin_p1", headers=clinician_headers)
    assert resp.status_code == 404


def test_cannot_update_another_accounts_patient(client, admin_headers, clinician_headers):
    client.post("/patients", json={"patient_id": "admin_p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.patch("/patients/admin_p1", json={"current_status": "discharged"}, headers=clinician_headers)
    assert resp.status_code == 404
    assert client.get("/patients/admin_p1", headers=admin_headers).json()["current_status"] == "active"


def test_cannot_delete_another_accounts_patient(client, admin_headers, clinician_headers):
    client.post("/patients", json={"patient_id": "admin_p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.delete("/patients/admin_p1", headers=clinician_headers)
    assert resp.status_code == 404
    assert client.get("/patients/admin_p1", headers=admin_headers).status_code == 200


def test_a_second_admin_does_not_see_the_first_admins_patients(client, admin_headers, test_db):
    """Privacy is per-ACCOUNT, not per-role -- two admins are just as isolated
    from each other as an admin and a clinician."""
    from src.api.security import create_access_token, hash_password
    from src.database.mongodb.repositories import UserRepository

    UserRepository(test_db).create("other_admin", hash_password("Password123!"), "admin")
    other_admin_headers = {"Authorization": f"Bearer {create_access_token('other_admin', 'admin')}"}

    client.post("/patients", json={"patient_id": "admin_p1", "source_dataset": "physionet_2019"}, headers=admin_headers)
    resp = client.get("/patients", headers=other_admin_headers)
    assert resp.json() == []

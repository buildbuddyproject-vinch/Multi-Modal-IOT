from src.api.security import hash_password
from src.database.mongodb.repositories import UserRepository


def _seed_admin(test_db, username="admin", password="adminpass123", role="admin"):
    UserRepository(test_db).create(username, hash_password(password), role)


def test_login_with_correct_credentials_returns_token(client, test_db):
    _seed_admin(test_db)
    resp = client.post("/auth/login", json={"username": "admin", "password": "adminpass123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"
    assert len(body["access_token"]) > 20


def test_login_with_wrong_password_rejected(client, test_db):
    _seed_admin(test_db)
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user_rejected(client):
    resp = client.post("/auth/login", json={"username": "ghost", "password": "whatever"})
    assert resp.status_code == 401


def test_me_requires_bearer_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, test_db):
    _seed_admin(test_db)
    token = client.post("/auth/login", json={"username": "admin", "password": "adminpass123"}).json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
    assert resp.json()["role"] == "admin"


def test_me_rejects_garbage_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert resp.status_code == 401


def test_register_requires_admin_role(client, test_db):
    _seed_admin(test_db, username="nurse", password="clinicianpass1", role="clinician")
    token = client.post("/auth/login", json={"username": "nurse", "password": "clinicianpass1"}).json()["access_token"]
    resp = client.post(
        "/auth/register",
        json={"username": "newuser", "password": "somepassword1", "role": "clinician"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_admin_can_register_new_user(client, test_db):
    _seed_admin(test_db)
    token = client.post("/auth/login", json={"username": "admin", "password": "adminpass123"}).json()["access_token"]
    resp = client.post(
        "/auth/register",
        json={"username": "dr_smith", "password": "somepassword1", "role": "clinician"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "clinician"

    login_resp = client.post("/auth/login", json={"username": "dr_smith", "password": "somepassword1"})
    assert login_resp.status_code == 200


def test_register_duplicate_username_rejected(client, test_db):
    _seed_admin(test_db)
    token = client.post("/auth/login", json={"username": "admin", "password": "adminpass123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/auth/register", json={"username": "dupe", "password": "somepassword1", "role": "clinician"}, headers=headers)
    resp = client.post("/auth/register", json={"username": "dupe", "password": "somepassword1", "role": "clinician"}, headers=headers)
    assert resp.status_code == 409


def test_list_users_requires_admin(client, test_db):
    _seed_admin(test_db)
    token = client.post("/auth/login", json={"username": "admin", "password": "adminpass123"}).json()["access_token"]
    resp = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()[0]["username"] == "admin"

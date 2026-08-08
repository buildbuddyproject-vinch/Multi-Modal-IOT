import mongomock
import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_db
from src.api.main import app
from src.api.security import create_access_token, hash_password
from src.database.mongodb.bootstrap import init_database
from src.database.mongodb.repositories import UserRepository


@pytest.fixture
def test_db():
    db = mongomock.MongoClient(tz_aware=True)["test_db"]
    init_database(db)
    return db


@pytest.fixture
def client(test_db):
    app.dependency_overrides[get_db] = lambda: test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(test_db):
    """Every patient-scoped route requires a real, authenticated owner --
    this is the default identity most route tests act as."""
    UserRepository(test_db).create("test_admin", hash_password("Password123!"), "admin")
    token = create_access_token("test_admin", "admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def clinician_headers(test_db):
    """A second, distinct identity -- used to prove ownership isolation
    (this user must NOT see the admin's patients, and vice versa)."""
    UserRepository(test_db).create("test_clinician", hash_password("Password123!"), "clinician")
    token = create_access_token("test_clinician", "clinician")
    return {"Authorization": f"Bearer {token}"}

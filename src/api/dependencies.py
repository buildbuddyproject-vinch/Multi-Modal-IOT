"""FastAPI dependency providers: one MongoDB database per app (via the cached
client), repositories built fresh per-request on top of it.

Every repo provider takes `db` via `Depends(get_db)` (rather than calling get_db()
directly) so that overriding `get_db` in tests (app.dependency_overrides[get_db] =
...) correctly propagates to every repository -- FastAPI only resolves overrides
for things declared as actual dependencies, not for plain function calls buried in
a provider's body.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from src.alerts.alert_engine import AlertEngine
from src.api.security import decode_access_token
from src.database.mongodb.connection import get_database
from src.database.mongodb.repositories import (
    AlertRepository,
    AuditLogRepository,
    PatientRepository,
    PredictionHistoryRepository,
    PredictionRepository,
    UserRepository,
    VitalsRepository,
)

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Database:
    return get_database()


def get_patient_repo(db: Database = Depends(get_db)) -> PatientRepository:
    return PatientRepository(db)


def get_vitals_repo(db: Database = Depends(get_db)) -> VitalsRepository:
    return VitalsRepository(db)


def get_prediction_repo(db: Database = Depends(get_db)) -> PredictionRepository:
    return PredictionRepository(db)


def get_prediction_history_repo(db: Database = Depends(get_db)) -> PredictionHistoryRepository:
    return PredictionHistoryRepository(db)


def get_alert_repo(db: Database = Depends(get_db)) -> AlertRepository:
    return AlertRepository(db)


def get_audit_repo(db: Database = Depends(get_db)) -> AuditLogRepository:
    return AuditLogRepository(db)


def get_user_repo(db: Database = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_alert_engine(
    alert_repo: AlertRepository = Depends(get_alert_repo),
    audit_repo: AuditLogRepository = Depends(get_audit_repo),
    vitals_repo: VitalsRepository = Depends(get_vitals_repo),
) -> AlertEngine:
    return AlertEngine(alert_repo, audit_repo, vitals_repo)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    repo: UserRepository = Depends(get_user_repo),
) -> dict:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token")
    user = repo.get_by_username(payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user no longer exists")
    return user


def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin role required")
    return user

from fastapi import APIRouter

from src.database.mongodb.connection import ping
from src.api.schemas.health import HealthOut

router = APIRouter(tags=["health"])

API_VERSION = "0.1.0"


@router.get("/health", response_model=HealthOut)
def health_check() -> HealthOut:
    mongo_ok = ping()
    return HealthOut(status="ok" if mongo_ok else "degraded", mongo_connected=mongo_ok, version=API_VERSION)

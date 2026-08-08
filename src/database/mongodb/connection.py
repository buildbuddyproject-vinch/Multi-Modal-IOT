"""MongoDB connection management. Sync (pymongo) client, matching what
mongomock mocks for unit tests -- Step 8's FastAPI layer decides sync-vs-async
usage on top of this."""
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from src.config.settings import get_settings


@lru_cache
def get_client() -> MongoClient:
    settings = get_settings()
    # tz_aware=True: without it pymongo decodes BSON dates as naive UTC datetimes,
    # which silently breaks comparisons against datetime.now(timezone.utc) (used
    # everywhere documents are created) with a TypeError or, worse, wrong results
    # if only one side is naive.
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000, tz_aware=True)


def get_database(client: MongoClient | None = None) -> Database:
    settings = get_settings()
    client = client or get_client()
    return client[settings.mongo_db_name]


def close_client() -> None:
    get_client().close()
    get_client.cache_clear()


def ping(client: MongoClient | None = None) -> bool:
    """Health check used by Step 8's /health endpoint and by scripts before
    running any database operation."""
    client = client or get_client()
    try:
        client.admin.command("ping")
        return True
    except Exception:
        return False

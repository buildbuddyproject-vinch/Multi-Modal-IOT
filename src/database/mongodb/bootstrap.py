"""Creates every collection (with its $jsonSchema validator) and index. Safe to
call repeatedly (idempotent) -- run once at application startup (FastAPI lifespan
in Step 8) or via scripts/init_mongodb.py.
"""
import logging

from pymongo.database import Database
from pymongo.errors import OperationFailure

from src.database.mongodb.indexes import create_all_indexes
from src.database.mongodb.schemas import COLLECTION_SCHEMAS

logger = logging.getLogger(__name__)


def init_database(db: Database) -> dict:
    existing = set(db.list_collection_names())
    created_collections = []
    validator_unsupported = []

    for name, schema in COLLECTION_SCHEMAS.items():
        if name in existing:
            continue
        try:
            db.create_collection(name, validator=schema)
        except (OperationFailure, NotImplementedError):
            # some test doubles (e.g. mongomock) don't implement $jsonSchema validators;
            # still create the collection so the rest of the app works against it.
            db.create_collection(name)
            validator_unsupported.append(name)
            logger.warning("Validator not supported for collection '%s' by this MongoDB backend; created without it", name)
        created_collections.append(name)

    index_result = create_all_indexes(db)

    return {
        "created_collections": created_collections,
        "validator_unsupported": validator_unsupported,
        "indexes": index_result,
    }

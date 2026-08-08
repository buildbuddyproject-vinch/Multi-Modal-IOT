import mongomock
import pytest

from src.database.mongodb.bootstrap import init_database
from src.database.mongodb.indexes import INDEX_SPECS
from src.database.mongodb.schemas import COLLECTION_SCHEMAS


@pytest.fixture
def db():
    return mongomock.MongoClient(tz_aware=True)["test_db"]


def test_init_database_creates_all_schema_collections(db):
    result = init_database(db)
    assert set(result["created_collections"]) == set(COLLECTION_SCHEMAS.keys())
    assert set(db.list_collection_names()) == set(COLLECTION_SCHEMAS.keys())


def test_init_database_is_idempotent(db):
    init_database(db)
    second_result = init_database(db)
    assert second_result["created_collections"] == []  # nothing new the second time


def test_init_database_creates_indexes_for_every_collection(db):
    result = init_database(db)
    for collection_name, specs in INDEX_SPECS.items():
        expected_names = {spec.document["name"] for spec in specs}
        assert expected_names <= set(result["indexes"][collection_name])


def test_patient_id_unique_index_enforced_even_by_mongomock(db):
    init_database(db)
    db["patients"].insert_one({"patient_id": "p1", "source_dataset": "physionet_2019"})
    with pytest.raises(Exception):
        db["patients"].insert_one({"patient_id": "p1", "source_dataset": "physionet_2019"})

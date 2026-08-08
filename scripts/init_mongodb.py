"""Step 7 CLI entry point: initialize the MongoDB database (collections, validators,
indexes) against whatever MONGO_URI/MONGO_DB_NAME .env points to.

Usage: python scripts/init_mongodb.py
"""
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_settings
from src.database.mongodb.bootstrap import init_database
from src.database.mongodb.connection import get_client, get_database, ping


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    client = get_client()
    if not ping(client):
        print(f"Could not reach MongoDB at {settings.mongo_uri}. "
              f"Start it with: docker compose -f deployment/docker/docker-compose.yml up -d mongo")
        sys.exit(1)

    db = get_database(client)
    result = init_database(db)
    print(f"Initialized database '{settings.mongo_db_name}' at {settings.mongo_uri}:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

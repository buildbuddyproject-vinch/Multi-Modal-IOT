"""Step 9 CLI entry point: provision the first admin account for the dashboard.
There is no open self-registration endpoint (POST /auth/register requires an
existing admin's JWT) -- this script is the one time auth is bootstrapped
directly against MongoDB.

Usage: python scripts/create_admin_user.py --username admin --password "S3curePass!"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.security import hash_password
from src.database.mongodb.bootstrap import init_database
from src.database.mongodb.connection import get_client, get_database, ping
from src.database.mongodb.repositories import UserRepository


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True, help="min 8 characters")
    parser.add_argument("--role", default="admin", choices=["admin", "clinician"])
    args = parser.parse_args()

    if len(args.password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    client = get_client()
    if not ping(client):
        print("Could not reach MongoDB. Start it with: docker compose -f deployment/docker/docker-compose.yml up -d mongo")
        sys.exit(1)

    db = get_database(client)
    init_database(db)
    repo = UserRepository(db)

    if repo.get_by_username(args.username) is not None:
        print(f"User '{args.username}' already exists.")
        sys.exit(1)

    repo.create(args.username, hash_password(args.password), args.role)
    print(f"Created {args.role} user '{args.username}'.")


if __name__ == "__main__":
    main()

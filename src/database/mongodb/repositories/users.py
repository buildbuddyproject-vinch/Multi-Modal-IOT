"""CRUD for the `users` collection (dashboard login, Step 9)."""
from datetime import datetime, timezone
from typing import Optional

from pymongo.database import Database


class UserRepository:
    def __init__(self, db: Database):
        self.collection = db["users"]

    def create(self, username: str, hashed_password: str, role: str) -> str:
        doc = {
            "username": username,
            "hashed_password": hashed_password,
            "role": role,
            "created_at": datetime.now(timezone.utc),
            "last_login": None,
        }
        result = self.collection.insert_one(doc)
        return str(result.inserted_id)

    def get_by_username(self, username: str) -> Optional[dict]:
        return self.collection.find_one({"username": username})

    def touch_last_login(self, username: str) -> None:
        self.collection.update_one({"username": username}, {"$set": {"last_login": datetime.now(timezone.utc)}})

    def count(self) -> int:
        return self.collection.count_documents({})

    def list_users(self, limit: int = 100) -> list[dict]:
        return list(self.collection.find({}).sort("username", 1).limit(limit))

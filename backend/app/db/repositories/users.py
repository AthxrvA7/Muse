"""The ``users`` collection: one document per Spotify account that has logged in."""

from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.db.models import SCHEMA_VERSION, User
from app.db.repositories._ids import to_object_id


def _to_user(document: dict[str, Any]) -> User:
    return User(
        id=str(document["_id"]),
        spotify_id=document["spotify_id"],
        display_name=document.get("display_name"),
        created_at=document["created_at"],
        last_login_at=document["last_login_at"],
    )


class UserRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._users = database["users"]

    async def upsert_on_login(
        self, spotify_id: str, display_name: str | None, now: datetime | None = None
    ) -> User:
        """Create the user on first login, or update the existing one. Atomic, so two
        logins at the same moment cannot create two users (the unique index also enforces it).
        """
        now = now or datetime.now(UTC)
        document = await self._users.find_one_and_update(
            {"spotify_id": spotify_id},
            {
                "$set": {"display_name": display_name, "last_login_at": now},
                "$setOnInsert": {"created_at": now, "schema_version": SCHEMA_VERSION},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return _to_user(document)

    async def get(self, user_id: str) -> User | None:
        object_id = to_object_id(user_id)
        if object_id is None:
            return None
        document = await self._users.find_one({"_id": object_id})
        return _to_user(document) if document else None

    async def delete(self, user_id: str) -> bool:
        object_id = to_object_id(user_id)
        if object_id is None:
            return False
        result = await self._users.delete_one({"_id": object_id})
        return result.deleted_count == 1

    async def save_tokens(self, user_id: str, tokens: dict[str, Any]) -> None:
        """Store the user's Spotify tokens. The caller passes them already encrypted."""
        object_id = to_object_id(user_id)
        if object_id is not None:
            await self._users.update_one({"_id": object_id}, {"$set": {"tokens": tokens}})

    async def get_tokens(self, user_id: str) -> dict[str, Any] | None:
        object_id = to_object_id(user_id)
        if object_id is None:
            return None
        document = await self._users.find_one({"_id": object_id}, projection={"tokens": True})
        tokens: dict[str, Any] | None = document.get("tokens") if document else None
        return tokens

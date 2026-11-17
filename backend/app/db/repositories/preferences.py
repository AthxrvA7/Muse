"""The ``preferences`` collection: one document per user with their stated taste."""

from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

from app.db.models import SCHEMA_VERSION, Preferences


class PreferencesRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._preferences = database["preferences"]

    async def get(self, user_id: str) -> Preferences | None:
        document: dict[str, Any] | None = await self._preferences.find_one(
            {"user_id": user_id}, projection={"_id": False, "schema_version": False}
        )
        return Preferences(**document) if document else None

    async def save(self, preferences: Preferences) -> None:
        """Create or replace the user's preferences (one document per user)."""
        await self._preferences.replace_one(
            {"user_id": preferences.user_id},
            {**preferences.model_dump(), "schema_version": SCHEMA_VERSION},
            upsert=True,
        )

    async def delete(self, user_id: str) -> bool:
        result = await self._preferences.delete_one({"user_id": user_id})
        return result.deleted_count == 1

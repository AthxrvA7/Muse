"""The ``recent_picks`` collection: which track IDs Muse recently picked for a user.

One document per user, holding at most the last 90 track IDs. Curate uses it to avoid
giving the same playlist twice. It expires 30 days after the last playlist (TTL index),
and is included in the data export and in account deletion.
"""

from datetime import UTC, datetime

from pymongo.asynchronous.database import AsyncDatabase

KEEP_LAST = 90


class RecentPicksRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._picks = database["recent_picks"]

    async def get(self, user_id: str) -> list[str]:
        document = await self._picks.find_one({"user_id": user_id}, projection={"_id": False})
        return list(document.get("track_ids", [])) if document else []

    async def remember(self, user_id: str, track_ids: list[str]) -> None:
        await self._picks.update_one(
            {"user_id": user_id},
            {
                "$push": {"track_ids": {"$each": track_ids, "$slice": -KEEP_LAST}},
                "$set": {"updated_at": datetime.now(UTC)},
            },
            upsert=True,
        )

    async def delete(self, user_id: str) -> bool:
        result = await self._picks.delete_one({"user_id": user_id})
        return result.deleted_count == 1

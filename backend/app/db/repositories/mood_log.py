"""The ``mood_log`` collection: one small entry per playlist a logged-in user curates.

Opt-in: nothing is logged until the user turns the trajectory on (``mood_settings``,
one document per user). Each entry holds the mood's valence and energy, its mood words
(from Muse's fixed list) and the playlist mode — never the text the user typed. Asking
again for the same mood within a few minutes ("Give me another") updates the last entry
instead of adding one.
Entries expire after 90 days (TTL index), are in the data export, and are deleted with
the account or with "Clear mood history".
"""

from datetime import UTC, datetime, timedelta

from pymongo.asynchronous.database import AsyncDatabase

from app.schemas.moods import MoodEntry

SAME_MOOD_WINDOW = timedelta(minutes=15)
MAX_POINTS = 500


class MoodLogRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._log = database["mood_log"]
        self._settings = database["mood_settings"]

    async def is_enabled(self, user_id: str) -> bool:
        settings = await self._settings.find_one({"_id": user_id})
        return bool(settings and settings.get("enabled"))

    async def set_enabled(self, user_id: str, enabled: bool) -> None:
        await self._settings.update_one(
            {"_id": user_id},
            {"$set": {"enabled": enabled, "updated_at": datetime.now(UTC)}},
            upsert=True,
        )

    async def record(self, user_id: str, entry: MoodEntry) -> None:
        """Logs the mood, only if the user turned the trajectory on."""
        if not await self.is_enabled(user_id):
            return
        document = {**entry.model_dump(), "user_id": user_id}
        last = await self._log.find_one({"user_id": user_id}, sort=[("at", -1)])
        if (
            last is not None
            and last.get("labels") == entry.labels
            and last.get("mode") == entry.mode
            and entry.at - last["at"] < SAME_MOOD_WINDOW
        ):
            await self._log.update_one({"_id": last["_id"]}, {"$set": document})
            return
        await self._log.insert_one(document)

    async def list_for_user(self, user_id: str, days: int) -> list[MoodEntry]:
        """Entries from the last ``days`` days, oldest first."""
        since = datetime.now(UTC) - timedelta(days=days)
        cursor = (
            self._log.find({"user_id": user_id, "at": {"$gte": since}}, projection={"_id": False})
            .sort("at", -1)
            .limit(MAX_POINTS)
        )
        newest_first = [MoodEntry.model_validate(document) async for document in cursor]
        return newest_first[::-1]

    async def delete_all(self, user_id: str) -> int:
        """For "Clear mood history": the entries go, the on/off choice stays."""
        result = await self._log.delete_many({"user_id": user_id})
        return result.deleted_count

    async def forget_user(self, user_id: str) -> int:
        """Account deletion: the entries and the on/off choice."""
        await self._settings.delete_one({"_id": user_id})
        return await self.delete_all(user_id)

"""The ``feedback`` collection: a user's 👍/👎 on songs, one document per user and song.

The document ID is ``user_id:track_id``, so rating a song again replaces the old rating.
Included in the data export and removed with the account; "Forget what Muse learned"
deletes all of it.
"""

from datetime import UTC, datetime

from pymongo.asynchronous.database import AsyncDatabase

from app.schemas.feedback import FeedbackIn, FeedbackRecord

MAX_REMEMBERED = 500  # the newest ratings Muse learns from


class FeedbackRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._feedback = database["feedback"]

    async def rate(self, user_id: str, rating: FeedbackIn) -> None:
        key = f"{user_id}:{rating.track_id}"
        if rating.value == 0:
            await self._feedback.delete_one({"_id": key})
            return
        document = {**rating.model_dump(), "user_id": user_id, "updated_at": datetime.now(UTC)}
        await self._feedback.replace_one({"_id": key}, document, upsert=True)

    async def list_for_user(self, user_id: str) -> list[FeedbackRecord]:
        cursor = (
            self._feedback.find({"user_id": user_id}, projection={"_id": False})
            .sort("updated_at", -1)
            .limit(MAX_REMEMBERED)
        )
        return [FeedbackRecord.model_validate(document) async for document in cursor]

    async def delete_all(self, user_id: str) -> int:
        result = await self._feedback.delete_many({"user_id": user_id})
        return result.deleted_count

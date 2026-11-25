"""The ``oauth_states`` collection: one document per login that has started but not finished.

Before sending the user to Spotify, Muse stores a random ``state``. Spotify sends it
back to the callback; Muse accepts the callback only if that state exists, and deletes
it in the same step so it can never be used twice (defence against login CSRF, T1).
"""

from datetime import UTC, datetime

from pymongo.asynchronous.database import AsyncDatabase

from app.db.models import SCHEMA_VERSION


class OAuthStateRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._states = database["oauth_states"]

    async def create(self, state: str, now: datetime | None = None) -> None:
        await self._states.insert_one(
            {
                "state": state,
                "created_at": now or datetime.now(UTC),
                "schema_version": SCHEMA_VERSION,
            }
        )

    async def consume(self, state: str) -> datetime | None:
        """Delete the state and return when it was created, or None if it is unknown
        or already used. Find-and-delete is one atomic operation.
        """
        document = await self._states.find_one_and_delete({"state": state})
        return document["created_at"] if document else None

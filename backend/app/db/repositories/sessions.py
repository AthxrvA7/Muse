"""The ``sessions`` collection: one document per logged-in browser.

The browser's cookie holds a random session ID; only its SHA-256 hash is stored here,
so a database leak does not reveal usable session IDs (ADR-0003). Hashing happens in
the auth service; this repository only ever sees the hash.
"""

from datetime import UTC, datetime
from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

from app.db.models import SCHEMA_VERSION, Session


def _to_session(document: dict[str, Any]) -> Session:
    return Session(
        id_hash=document["id_hash"],
        user_id=document["user_id"],
        created_at=document["created_at"],
        last_seen_at=document["last_seen_at"],
    )


class SessionRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._sessions = database["sessions"]

    async def create(self, id_hash: str, user_id: str, now: datetime | None = None) -> Session:
        now = now or datetime.now(UTC)
        session = Session(id_hash=id_hash, user_id=user_id, created_at=now, last_seen_at=now)
        await self._sessions.insert_one({**session.model_dump(), "schema_version": SCHEMA_VERSION})
        return session

    async def get(self, id_hash: str) -> Session | None:
        document = await self._sessions.find_one({"id_hash": id_hash})
        return _to_session(document) if document else None

    async def touch(self, id_hash: str, now: datetime | None = None) -> bool:
        """Record activity, which restarts the 7-day idle timer (TTL index)."""
        result = await self._sessions.update_one(
            {"id_hash": id_hash}, {"$set": {"last_seen_at": now or datetime.now(UTC)}}
        )
        return result.matched_count == 1

    async def delete(self, id_hash: str) -> bool:
        """Log out one browser. Takes effect immediately."""
        result = await self._sessions.delete_one({"id_hash": id_hash})
        return result.deleted_count == 1

    async def delete_all_for_user(self, user_id: str) -> int:
        """Log out everywhere (also used by account deletion)."""
        result = await self._sessions.delete_many({"user_id": user_id})
        return result.deleted_count

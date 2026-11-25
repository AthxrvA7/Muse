"""In-memory stand-ins for the MongoDB repositories, for fast tests without a database.

They mirror the real repositories' behaviour that the services rely on; the real ones
are tested against MongoDB in test_repositories.py (pytest --db).
"""

from datetime import UTC, datetime
from typing import Any

from app.db.models import PlaylistRecord, Preferences, Session, User


class FakeUsers:
    def __init__(self) -> None:
        self.by_id: dict[str, User] = {}
        self.tokens: dict[str, dict[str, Any]] = {}

    async def upsert_on_login(
        self, spotify_id: str, display_name: str | None, now: datetime | None = None
    ) -> User:
        now = now or datetime.now(UTC)
        existing = next((u for u in self.by_id.values() if u.spotify_id == spotify_id), None)
        user = User(
            id=existing.id if existing else f"user-{len(self.by_id) + 1}",
            spotify_id=spotify_id,
            display_name=display_name,
            created_at=existing.created_at if existing else now,
            last_login_at=now,
        )
        self.by_id[user.id] = user
        return user

    async def get(self, user_id: str) -> User | None:
        return self.by_id.get(user_id)

    async def delete(self, user_id: str) -> bool:
        self.tokens.pop(user_id, None)
        return self.by_id.pop(user_id, None) is not None

    async def save_tokens(self, user_id: str, tokens: dict[str, Any]) -> None:
        self.tokens[user_id] = tokens

    async def get_tokens(self, user_id: str) -> dict[str, Any] | None:
        return self.tokens.get(user_id)


class FakeSessions:
    def __init__(self) -> None:
        self.by_hash: dict[str, Session] = {}

    async def create(self, id_hash: str, user_id: str, now: datetime | None = None) -> Session:
        now = now or datetime.now(UTC)
        session = Session(id_hash=id_hash, user_id=user_id, created_at=now, last_seen_at=now)
        self.by_hash[id_hash] = session
        return session

    async def get(self, id_hash: str) -> Session | None:
        return self.by_hash.get(id_hash)

    async def touch(self, id_hash: str, now: datetime | None = None) -> bool:
        session = self.by_hash.get(id_hash)
        if session is None:
            return False
        self.by_hash[id_hash] = session.model_copy(
            update={"last_seen_at": now or datetime.now(UTC)}
        )
        return True

    async def delete(self, id_hash: str) -> bool:
        return self.by_hash.pop(id_hash, None) is not None

    async def delete_all_for_user(self, user_id: str) -> int:
        doomed = [h for h, s in self.by_hash.items() if s.user_id == user_id]
        for id_hash in doomed:
            del self.by_hash[id_hash]
        return len(doomed)


class FakeStates:
    def __init__(self) -> None:
        self.created: dict[str, datetime] = {}

    async def create(self, state: str, now: datetime | None = None) -> None:
        self.created[state] = now or datetime.now(UTC)

    async def consume(self, state: str) -> datetime | None:
        return self.created.pop(state, None)


class FakePreferences:
    def __init__(self) -> None:
        self.by_user: dict[str, Preferences] = {}

    async def get(self, user_id: str) -> Preferences | None:
        return self.by_user.get(user_id)

    async def save(self, preferences: Preferences) -> None:
        self.by_user[preferences.user_id] = preferences

    async def delete(self, user_id: str) -> bool:
        return self.by_user.pop(user_id, None) is not None


class FakePlaylists:
    def __init__(self) -> None:
        self.records: list[PlaylistRecord] = []

    async def add(self, record: PlaylistRecord) -> PlaylistRecord:
        saved = record.model_copy(update={"id": f"pl-{len(self.records) + 1}"})
        self.records.append(saved)
        return saved

    async def list_for_user(self, user_id: str, limit: int = 20) -> list[PlaylistRecord]:
        mine = [r for r in self.records if r.user_id == user_id]
        return sorted(mine, key=lambda r: r.created_at, reverse=True)[:limit]

    async def delete_all_for_user(self, user_id: str) -> int:
        before = len(self.records)
        self.records = [r for r in self.records if r.user_id != user_id]
        return before - len(self.records)

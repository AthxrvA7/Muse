"""Index definitions: the database itself must enforce uniqueness and expiry."""

import pytest

from app.db.indexes import (
    INDEXES,
    OAUTH_STATE_SECONDS,
    SESSION_IDLE_SECONDS,
    ensure_indexes,
)


class RecordingCollection:
    def __init__(self, name: str, calls: list[tuple[str, object, dict[str, object]]]) -> None:
        self.name = name
        self.calls = calls

    async def create_index(self, keys: object, **options: object) -> str:
        self.calls.append((self.name, keys, options))
        return str(options["name"])


class RecordingDatabase:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, dict[str, object]]] = []

    def __getitem__(self, name: str) -> RecordingCollection:
        return RecordingCollection(name, self.calls)


def _spec(collection: str, field: str):  # type: ignore[no-untyped-def]
    return next(s for s in INDEXES if s.collection == collection and s.field == field)


@pytest.mark.parametrize(
    ("collection", "field"),
    [
        ("users", "spotify_id"),
        ("sessions", "id_hash"),
        ("oauth_states", "state"),
        ("preferences", "user_id"),
    ],
)
def test_identity_fields_are_unique(collection: str, field: str) -> None:
    assert _spec(collection, field).unique is True


def test_sessions_expire_after_seven_idle_days() -> None:
    spec = _spec("sessions", "last_seen_at")

    assert spec.expire_after_seconds == SESSION_IDLE_SECONDS == 7 * 24 * 60 * 60


def test_pending_logins_expire_after_ten_minutes() -> None:
    spec = _spec("oauth_states", "created_at")

    assert spec.expire_after_seconds == OAUTH_STATE_SECONDS == 600


def test_index_names_are_unique_per_collection() -> None:
    keys = [(spec.collection, spec.name) for spec in INDEXES]

    assert len(keys) == len(set(keys))


@pytest.mark.anyio
async def test_ensure_indexes_creates_every_index() -> None:
    database = RecordingDatabase()

    await ensure_indexes(database)  # type: ignore[arg-type]

    assert len(database.calls) == len(INDEXES)
    assert (
        "sessions",
        [("last_seen_at", 1)],
        {
            "name": "idle_ttl",
            "unique": False,
            "expireAfterSeconds": SESSION_IDLE_SECONDS,
        },
    ) in database.calls
    assert ("users", [("spotify_id", 1)], {"name": "spotify_id_unique", "unique": True}) in (
        database.calls
    )

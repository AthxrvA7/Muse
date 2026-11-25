"""Repository tests against a real MongoDB.

``mongomock`` does not support PyMongo's async API (ADR-0004), so these tests need a
real database. They are skipped unless pytest is run with ``--db``:

    pytest --db

They then use MONGODB_URI from .env, work in a throwaway database named
``muse_test_<random>``, and drop its collections afterwards. The real ``muse``
database is never touched. CI runs them with ``--db`` against a throwaway MongoDB
service container (MONGODB_URI set as an environment variable), so it never needs
the Atlas secret.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.core.config import Settings
from app.db.indexes import OAUTH_STATE_SECONDS, SESSION_IDLE_SECONDS, ensure_indexes
from app.db.models import SCHEMA_VERSION, PlaylistRecord, Preferences
from app.db.mongo import create_client
from app.db.repositories.oauth_states import OAuthStateRepository
from app.db.repositories.playlists import PlaylistRepository
from app.db.repositories.preferences import PreferencesRepository
from app.db.repositories.recent_picks import RecentPicksRepository
from app.db.repositories.sessions import SessionRepository
from app.db.repositories.users import UserRepository

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def database(request: pytest.FixtureRequest) -> AsyncIterator[AsyncDatabase]:
    if not request.config.getoption("--db"):
        pytest.skip("needs a real MongoDB: run pytest --db")
    settings = Settings()  # reads MONGODB_URI from .env on purpose
    if not settings.mongodb_configured:
        pytest.fail("pytest --db needs MONGODB_URI in .env")

    client = create_client(settings)
    test_database = client[f"muse_test_{uuid4().hex[:8]}"]
    await ensure_indexes(test_database)
    try:
        yield test_database
    finally:
        for name in await test_database.list_collection_names():
            await test_database.drop_collection(name)
        await client.close()


def _now() -> datetime:
    # Current time (so TTL indexes don't delete test documents mid-test), at MongoDB's
    # millisecond precision so values compare equal after a round trip.
    return datetime.now(UTC).replace(microsecond=0)


# ---------------------------------------------------------------- indexes


async def test_indexes_exist_with_the_right_options(database: AsyncDatabase) -> None:
    await ensure_indexes(database)  # a second run must be a harmless no-op

    users = await database["users"].index_information()
    sessions = await database["sessions"].index_information()
    states = await database["oauth_states"].index_information()

    assert users["spotify_id_unique"]["unique"] is True
    assert sessions["idle_ttl"]["expireAfterSeconds"] == SESSION_IDLE_SECONDS
    assert states["pending_ttl"]["expireAfterSeconds"] == OAUTH_STATE_SECONDS


# ---------------------------------------------------------------- users


async def test_first_login_creates_a_user_and_later_logins_update_it(
    database: AsyncDatabase,
) -> None:
    users = UserRepository(database)
    first, later = _now(), _now() + timedelta(minutes=5)

    created = await users.upsert_on_login("spotify-user-1", "Atharva", now=first)
    updated = await users.upsert_on_login("spotify-user-1", "Ath", now=later)

    assert updated.id == created.id
    assert updated.display_name == "Ath"
    assert updated.created_at == first
    assert updated.last_login_at == later
    assert await database["users"].count_documents({}) == 1
    stored = await database["users"].find_one({"spotify_id": "spotify-user-1"})
    assert stored is not None
    assert stored["schema_version"] == SCHEMA_VERSION


async def test_user_can_be_read_and_deleted(database: AsyncDatabase) -> None:
    users = UserRepository(database)
    user = await users.upsert_on_login("spotify-user-2", None)

    assert await users.get(user.id) == user
    assert await users.delete(user.id) is True
    assert await users.get(user.id) is None
    assert await users.delete(user.id) is False


async def test_encrypted_tokens_are_stored_on_the_user(database: AsyncDatabase) -> None:
    users = UserRepository(database)
    user = await users.upsert_on_login("spotify-user-4", "Ath")
    tokens = {"access_token": "enc-a", "refresh_token": "enc-r", "expires_at": 1.0, "scope": ""}

    await users.save_tokens(user.id, tokens)

    assert await users.get_tokens(user.id) == tokens
    assert await users.get(user.id) == user  # tokens never leak into the User model
    assert await users.get_tokens("not-an-id") is None


async def test_unknown_or_malformed_user_ids_return_nothing(database: AsyncDatabase) -> None:
    users = UserRepository(database)

    assert await users.get("6553f0f0f0f0f0f0f0f0f0f0") is None
    assert await users.get("not-an-id") is None
    assert await users.delete("not-an-id") is False


async def test_database_refuses_two_users_for_one_spotify_account(
    database: AsyncDatabase,
) -> None:
    await database["users"].insert_one({"spotify_id": "spotify-user-3"})

    with pytest.raises(DuplicateKeyError):
        await database["users"].insert_one({"spotify_id": "spotify-user-3"})


# ---------------------------------------------------------------- sessions


async def test_session_lifecycle(database: AsyncDatabase) -> None:
    sessions = SessionRepository(database)
    start, later = _now(), _now() + timedelta(hours=1)

    created = await sessions.create("hash-1", "user-1", now=start)
    assert await sessions.get("hash-1") == created

    assert await sessions.touch("hash-1", now=later) is True
    touched = await sessions.get("hash-1")
    assert touched is not None
    assert touched.last_seen_at == later
    assert touched.created_at == start

    assert await sessions.delete("hash-1") is True
    assert await sessions.get("hash-1") is None
    assert await sessions.touch("hash-1") is False


async def test_log_out_everywhere_removes_only_that_users_sessions(
    database: AsyncDatabase,
) -> None:
    sessions = SessionRepository(database)
    await sessions.create("hash-a", "user-1")
    await sessions.create("hash-b", "user-1")
    await sessions.create("hash-c", "user-2")

    assert await sessions.delete_all_for_user("user-1") == 2
    assert await sessions.get("hash-c") is not None


async def test_session_hashes_are_unique(database: AsyncDatabase) -> None:
    sessions = SessionRepository(database)
    await sessions.create("hash-dup", "user-1")

    with pytest.raises(DuplicateKeyError):
        await sessions.create("hash-dup", "user-2")


# ---------------------------------------------------------------- OAuth states


async def test_oauth_state_can_be_used_only_once(database: AsyncDatabase) -> None:
    states = OAuthStateRepository(database)
    created_at = _now()
    await states.create("state-1", now=created_at)

    assert await states.consume("state-1") == created_at
    assert await states.consume("state-1") is None


async def test_unknown_oauth_state_is_rejected(database: AsyncDatabase) -> None:
    assert await OAuthStateRepository(database).consume("never-issued") is None


# ---------------------------------------------------------------- preferences


async def test_preferences_are_saved_replaced_and_deleted(database: AsyncDatabase) -> None:
    preferences = PreferencesRepository(database)
    first = Preferences(
        user_id="user-1",
        artists=["Prateek Kuhad"],
        genres=["indie folk"],
        languages=["hi", "en"],
        updated_at=_now(),
    )
    second = first.model_copy(update={"genres": ["lo-fi"], "artists": []})

    assert await preferences.get("user-1") is None
    await preferences.save(first)
    assert await preferences.get("user-1") == first

    await preferences.save(second)
    assert await preferences.get("user-1") == second
    assert await database["preferences"].count_documents({"user_id": "user-1"}) == 1

    assert await preferences.delete("user-1") is True
    assert await preferences.get("user-1") is None


# ---------------------------------------------------------------- playlists


async def test_playlist_history_is_per_user_and_newest_first(database: AsyncDatabase) -> None:
    playlists = PlaylistRepository(database)
    older, newer = _now() - timedelta(days=1), _now()

    def record(user_id: str, name: str, at: datetime) -> PlaylistRecord:
        return PlaylistRecord(
            user_id=user_id,
            spotify_playlist_id=f"sp-{name}",
            url=f"https://open.spotify.com/playlist/sp-{name}",
            name=name,
            track_count=15,
            created_at=at,
        )

    saved = await playlists.add(record("user-1", "old", older))
    await playlists.add(record("user-1", "new", newer))
    await playlists.add(record("user-2", "other", newer))

    history = await playlists.list_for_user("user-1")

    assert saved.id is not None
    assert [p.name for p in history] == ["new", "old"]
    assert await playlists.delete_all_for_user("user-1") == 2


# ---------------------------------------------------------------- recent picks


async def test_recent_picks_keep_the_latest_90_per_user(database: AsyncDatabase) -> None:
    picks = RecentPicksRepository(database)

    await picks.remember("user-1", [f"a{i}" for i in range(60)])
    await picks.remember("user-1", [f"b{i}" for i in range(60)])
    await picks.remember("user-2", ["other"])

    kept = await picks.get("user-1")
    assert len(kept) == 90
    assert kept[-1] == "b59" and "a0" not in kept  # oldest dropped first
    assert await picks.get("nobody") == []
    assert await picks.delete("user-1") is True
    assert await picks.get("user-1") == []

"""Download my data and delete my account (FR11), with in-memory storage."""

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import current_user, get_privacy_service
from app.core.config import Settings
from app.db.models import PlaylistRecord, Preferences
from app.main import create_app
from app.services.privacy import PrivacyService
from tests.fakes import FakePlaylists, FakePreferences, FakeSessions, FakeUsers

NOW = datetime(2026, 11, 25, tzinfo=UTC)


class World:
    def __init__(self) -> None:
        self.users, self.sessions = FakeUsers(), FakeSessions()
        self.preferences, self.playlists = FakePreferences(), FakePlaylists()

    async def seed(self) -> None:
        self.user = await self.users.upsert_on_login("spotify-ath", "Ath", now=NOW)
        other = await self.users.upsert_on_login("spotify-other", "Other", now=NOW)
        await self.users.save_tokens(self.user.id, {"refresh_token": "encrypted-secret"})
        await self.sessions.create("hash-1", self.user.id)
        await self.sessions.create("hash-2", self.user.id)
        await self.sessions.create("hash-other", other.id)
        await self.preferences.save(
            Preferences(user_id=self.user.id, artists=["Prateek Kuhad"], updated_at=NOW)
        )
        await self.playlists.add(
            PlaylistRecord(
                user_id=self.user.id,
                spotify_playlist_id="3cEYpjA9oz9GiPac4AsH4n",
                url="https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n",
                name="Muse: calm",
                track_count=15,
                created_at=NOW,
            )
        )

    def client(self) -> TestClient:
        service = PrivacyService(self.users, self.sessions, self.preferences, self.playlists)
        app = create_app(Settings(_env_file=None, app_env="test"))
        app.dependency_overrides[current_user] = lambda: self.user
        app.dependency_overrides[get_privacy_service] = lambda: service
        return TestClient(app)


@pytest.fixture
async def world() -> World:
    w = World()
    await w.seed()
    return w


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_export_contains_everything_and_no_tokens(world: World) -> None:
    response = world.client().get("/api/v1/me/data")

    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    data = json.loads(response.text)
    assert data["account"]["spotify_id"] == "spotify-ath"
    assert data["preferences"]["artists"] == ["Prateek Kuhad"]
    assert data["playlists_created_by_muse"][0]["name"] == "Muse: calm"
    assert "encrypted-secret" not in response.text
    assert "the text you type about your mood" in data["not_stored"]


@pytest.mark.anyio
async def test_delete_removes_every_document_for_that_user_only(world: World) -> None:
    response = world.client().delete("/api/v1/me")

    assert response.status_code == 204
    assert 'muse_session=""' in response.headers["set-cookie"]
    assert response.headers["X-Deleted"] == "playlists=1,preferences=1,sessions=2,account=1"
    assert world.user.id not in world.users.by_id
    assert world.user.id not in world.users.tokens
    assert world.preferences.by_user == {}
    assert world.playlists.records == []
    assert list(world.sessions.by_hash) == ["hash-other"]  # other users untouched
    assert len(world.users.by_id) == 1


def test_privacy_endpoints_need_a_login(client: TestClient) -> None:
    assert client.get("/api/v1/me/data").status_code in (401, 503)
    assert client.delete("/api/v1/me").status_code in (401, 503)


def test_recent_picks_are_exported_and_deleted() -> None:
    import asyncio

    class Recent:
        def __init__(self) -> None:
            self.ids = ["t1", "t2"]

        async def get(self, user_id: str) -> list[str]:
            return self.ids

        async def delete(self, user_id: str) -> bool:
            self.ids = []
            return True

    async def run() -> tuple[dict, dict]:  # type: ignore[type-arg]
        world = World()
        await world.seed()
        service = PrivacyService(
            world.users, world.sessions, world.preferences, world.playlists, recent
        )
        return await service.export(world.user), await service.delete_account(world.user)

    recent = Recent()
    exported, removed = asyncio.run(run())

    assert exported["recently_picked_track_ids"] == ["t1", "t2"]
    assert removed["recent_picks"] == 1
    assert recent.ids == []


def test_mood_history_is_exported_and_deleted() -> None:
    import asyncio

    from tests.test_trajectory import FakeMoodLog, entry

    async def run() -> tuple[dict, dict]:  # type: ignore[type-arg]
        world = World()
        await world.seed()
        await moods.set_enabled(world.user.id, True)
        await moods.record(world.user.id, entry(0, 0.3, 0.6, "low"))
        service = PrivacyService(
            world.users, world.sessions, world.preferences, world.playlists, moods=moods
        )
        return await service.export(world.user), await service.delete_account(world.user)

    moods = FakeMoodLog()
    exported, removed = asyncio.run(run())

    assert exported["mood_trajectory_on"] is True
    (point,) = exported["mood_history"]
    assert point["labels"] == ["low"] and point["valence"] == 0.3
    assert removed["mood_history"] == 1
    assert moods.entries == {} and moods.enabled == {}

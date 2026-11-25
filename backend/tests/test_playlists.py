"""Saving a curated playlist to the user's Spotify account (fake Spotify, in-memory storage)."""

import json
from datetime import UTC, datetime

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.api.deps import current_user, get_playlist_service
from app.clients.spotify_user import SpotifyLoginError
from app.core.config import Settings
from app.db.models import User
from app.main import create_app
from app.services.auth import NotLoggedInError
from app.services.playlists import PlaylistService
from tests.fakes import FakePlaylists

USER = User(
    id="user-1",
    spotify_id="spotify-ath",
    display_name="Ath",
    created_at=datetime(2026, 11, 25, tzinfo=UTC),
    last_login_at=datetime(2026, 11, 25, tzinfo=UTC),
)
TRACKS = ["4uLU6hMCjMI75M1A2tKUQC", "7ouMYWpwJ422jRcDASZB7P"]


class FakeTokens:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def access_token(self, user_id: str) -> str:
        if self.error:
            raise self.error
        return "user-token"


class FakeSpotifyPlaylists:
    def __init__(self, add_status: int = 201) -> None:
        self.add_status = add_status
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if request.url.path == "/v1/me/playlists":
            return httpx2.Response(
                201,
                json={
                    "id": "spotify-pl-1",
                    "external_urls": {"spotify": "https://open.spotify.com/playlist/spotify-pl-1"},
                },
            )
        return httpx2.Response(self.add_status, json={"snapshot_id": "s"})


class World:
    def __init__(self, tokens: FakeTokens | None = None, add_status: int = 201) -> None:
        self.spotify = FakeSpotifyPlaylists(add_status)
        self.store = FakePlaylists()
        http = httpx2.AsyncClient(transport=httpx2.MockTransport(self.spotify))
        service = PlaylistService(tokens or FakeTokens(), http, self.store)  # type: ignore[arg-type]
        app = create_app(Settings(_env_file=None, app_env="test"))
        app.dependency_overrides[current_user] = lambda: USER
        app.dependency_overrides[get_playlist_service] = lambda: service
        self.client = TestClient(app)


def test_playlist_is_created_in_spotify_and_recorded() -> None:
    world = World()

    response = world.client.post(
        "/api/v1/playlists", json={"name": "Muse: calm", "track_ids": TRACKS + [TRACKS[0]]}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://open.spotify.com/playlist/spotify-pl-1"
    assert body["track_count"] == 2  # duplicate removed
    create, add = world.spotify.requests
    assert create.headers["Authorization"] == "Bearer user-token"
    assert json.loads(create.content)["public"] is False
    assert json.loads(add.content)["uris"] == [f"spotify:track:{t}" for t in TRACKS]
    assert world.store.records[0].spotify_playlist_id == "spotify-pl-1"


def test_history_lists_saved_playlists() -> None:
    world = World()
    world.client.post("/api/v1/playlists", json={"name": "First", "track_ids": TRACKS})
    world.client.post("/api/v1/playlists", json={"name": "Second", "track_ids": TRACKS})

    names = [p["name"] for p in world.client.get("/api/v1/playlists").json()]

    assert sorted(names) == ["First", "Second"]


@pytest.mark.parametrize(
    "body",
    [
        {"name": "x", "track_ids": []},
        {"name": "x", "track_ids": ["not-a-spotify-id"]},
        {"name": "", "track_ids": TRACKS},
        {"name": "x", "track_ids": TRACKS, "public": True},
    ],
)
def test_bad_export_requests_are_rejected(body: dict[str, object]) -> None:
    assert World().client.post("/api/v1/playlists", json=body).status_code == 422


def test_expired_login_asks_to_log_in_again() -> None:
    for error in (NotLoggedInError("x"), SpotifyLoginError("x")):
        world = World(tokens=FakeTokens(error))

        response = world.client.post("/api/v1/playlists", json={"name": "n", "track_ids": TRACKS})

        assert response.status_code == 401
        assert world.store.records == []


def test_spotify_refusal_is_explained_and_nothing_is_recorded() -> None:
    world = World(add_status=403)

    response = world.client.post("/api/v1/playlists", json={"name": "n", "track_ids": TRACKS})

    assert response.status_code == 403
    assert "Users Management" in response.json()["detail"]["message"]
    assert world.store.records == []


def test_saving_a_playlist_needs_a_login() -> None:
    client = TestClient(create_app(Settings(_env_file=None, app_env="test")))

    response = client.post("/api/v1/playlists", json={"name": "n", "track_ids": TRACKS})

    assert response.status_code in (401, 503)

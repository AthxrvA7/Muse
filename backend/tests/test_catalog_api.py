"""HTTP tests for GET /api/v1/catalog/search (Spotify replaced by a fake)."""

from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clients.spotify import TOKEN_URL, SpotifyRateLimitError, SpotifyUnavailableError
from app.core.config import Settings
from app.main import create_app
from app.schemas.catalog import Artist, ArtistRef, Track
from app.services.catalog import get_catalog_service

URL = "/api/v1/catalog/search"

TRACK = Track(
    id="t1",
    name="cold/mess",
    artists=[ArtistRef(id="a1", name="Prateek Kuhad")],
    album="cold/mess",
    release_year=2018,
    image_url=None,
    spotify_url="https://open.spotify.com/track/t1",
    uri="spotify:track:t1",
    explicit=False,
    duration_ms=240_000,
)
ARTIST = Artist(
    id="a1",
    name="Prateek Kuhad",
    genres=[],
    image_url=None,
    spotify_url="https://open.spotify.com/artist/a1",
)


class FakeCatalog:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str, int]] = []

    async def search(self, query: str, kind: str, limit: int) -> list[Track] | list[Artist]:
        self.calls.append((query, kind, limit))
        if self.error:
            raise self.error
        return [ARTIST] if kind == "artist" else [TRACK]


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


def test_track_search_returns_tracks(app: FastAPI) -> None:
    fake = FakeCatalog()
    app.dependency_overrides[get_catalog_service] = lambda: fake

    response = TestClient(app).get(URL, params={"q": "prateek"})

    assert response.status_code == 200
    assert response.json()[0]["name"] == "cold/mess"
    assert fake.calls == [("prateek", "track", 10)]


def test_artist_search_returns_artists(app: FastAPI) -> None:
    fake = FakeCatalog()
    app.dependency_overrides[get_catalog_service] = lambda: fake

    response = TestClient(app).get(URL, params={"q": "prateek", "type": "artist", "limit": 5})

    assert response.json()[0]["name"] == "Prateek Kuhad"
    assert fake.calls == [("prateek", "artist", 5)]


@pytest.mark.parametrize(
    "params",
    [
        {"q": ""},
        {"q": "x" * 101},
        {"q": "x", "limit": 0},
        {"q": "x", "limit": 21},
        {"q": "x", "type": "album"},
    ],
)
def test_invalid_queries_are_rejected(app: FastAPI, params: dict[str, str | int]) -> None:
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalog()

    assert TestClient(app).get(URL, params=params).status_code == 422


def test_missing_spotify_credentials_give_503(client: TestClient) -> None:
    response = client.get(URL, params={"q": "anything"})  # test settings have no Spotify keys

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]["message"]


def test_spotify_outage_gives_503_without_internal_details(app: FastAPI) -> None:
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalog(
        SpotifyUnavailableError("upstream returned 502 at api.spotify.com")
    )

    response = TestClient(app).get(URL, params={"q": "x"})

    assert response.status_code == 503
    assert "502" not in response.text


def test_spotify_rate_limit_gives_429_with_retry_after(app: FastAPI) -> None:
    app.dependency_overrides[get_catalog_service] = lambda: FakeCatalog(SpotifyRateLimitError(7))

    response = TestClient(app).get(URL, params={"q": "x"})

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "7"


def test_full_chain_from_settings_to_spotify_with_only_the_network_faked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[httpx2.Request] = []

    def spotify(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        if str(request.url) == TOKEN_URL:
            return httpx2.Response(200, json={"access_token": "tok", "expires_in": 3600})
        item = TRACK.model_dump()
        item.update(
            artists=[{"id": "a1", "name": "Prateek Kuhad"}],
            album={"name": "cold/mess", "release_date": "2018", "images": []},
            external_urls={"spotify": TRACK.spotify_url},
        )
        return httpx2.Response(200, json={"tracks": {"items": [item]}})

    real_client = httpx2.AsyncClient

    def fake_client(**kwargs: Any) -> httpx2.AsyncClient:
        return real_client(transport=httpx2.MockTransport(spotify), **kwargs)

    monkeypatch.setattr("app.services.spotify_session.httpx2.AsyncClient", fake_client)
    settings = Settings(
        _env_file=None,
        app_env="test",
        spotify_client_id="id",
        spotify_client_secret="secret",
        spotify_market="GB",
    )

    response = TestClient(create_app(settings)).get(URL, params={"q": 'prateek "kuhad"'})

    assert response.status_code == 200
    assert response.json()[0]["release_year"] == 2018
    search = seen[-1].url.params
    assert search["q"] == "prateek kuhad"  # quotes stripped by the query builder
    assert search["market"] == "GB"

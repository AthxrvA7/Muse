"""End-to-end tests for POST /api/v1/curate: real Muse logic, fake Spotify catalogue."""

import asyncio
import re
import time
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clients.spotify import TOKEN_URL, SpotifyRateLimitError
from app.core.config import Settings
from app.main import create_app
from app.schemas.catalog import Track
from app.services.curate import CurateService, get_curate_service
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.vocabulary import load_vocabulary
from app.services.recommender.knowledge import load_genre_knowledge
from tests.recommender_fixtures import track

URL = "/api/v1/curate"
KB = load_genre_knowledge()


class FakeCatalogue:
    """Answers artist:"X" with 8 songs by X and genre:"g" with 12 songs by 6 artists."""

    def __init__(self, delay: float = 0.0, error: Exception | None = None, per_genre: int = 12):
        self.delay, self.error, self.per_genre = delay, error, per_genre
        self.queries: list[str] = []

    async def search_tracks(self, query: str, total: int = 10) -> list[Track]:
        self.queries.append(query)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        if m := re.fullmatch(r'artist:"(.+)"', query):
            name = m.group(1)
            return [track(f"{name}-{i}", name, f"{name} song {i}") for i in range(8)]
        if m := re.fullmatch(r'genre:"(.+)"', query):
            g = m.group(1)
            return [
                track(f"{g}-{i}", f"{g} artist {i % 6}", f"{g} tune {i}")
                for i in range(self.per_genre)
            ]
        return []


def client_with(app: FastAPI, catalogue: FakeCatalogue) -> TestClient:
    service = CurateService(catalogue, MoodAnalyzer(load_vocabulary()), KB)
    app.dependency_overrides[get_curate_service] = lambda: service
    return TestClient(app)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


CALM_REQUEST: dict[str, Any] = {
    "mood": {"chips": ["tired", "low"]},
    "taste": {"artists": ["Prateek Kuhad"], "genres": ["lo-fi", "metal", "indie folk"]},
    "size": 12,
}


def test_curate_returns_the_requested_number_of_explained_tracks(app: FastAPI) -> None:
    body = client_with(app, FakeCatalogue()).post(URL, json=CALM_REQUEST).json()

    assert len(body["tracks"]) == 12
    assert all(t["reason"] for t in body["tracks"])
    assert body["mood"]["tempo"] == "slow"
    assert body["note"] is None


def test_no_artist_appears_more_than_twice(app: FastAPI) -> None:
    body = client_with(app, FakeCatalogue()).post(URL, json=CALM_REQUEST).json()

    artists = [t["track"]["artists"][0]["name"] for t in body["tracks"]]
    assert max(artists.count(a) for a in artists) <= 2


def test_favourite_artist_is_included_and_named_in_the_reason(app: FastAPI) -> None:
    body = client_with(app, FakeCatalogue()).post(URL, json=CALM_REQUEST).json()

    prateek = [t for t in body["tracks"] if t["track"]["artists"][0]["name"] == "Prateek Kuhad"]
    assert len(prateek) == 2
    assert "you like Prateek Kuhad" in prateek[0]["reason"]


def test_a_tired_mood_prefers_quiet_genres_over_metal(app: FastAPI) -> None:
    body = client_with(app, FakeCatalogue()).post(URL, json=CALM_REQUEST).json()

    names = [t["track"]["name"] for t in body["tracks"]]
    first_lofi = next(i for i, n in enumerate(names) if n.startswith("lo-fi"))
    metal = [i for i, n in enumerate(names) if n.startswith("metal")]
    assert all(first_lofi < i for i in metal)


def test_excluded_artists_never_appear(app: FastAPI) -> None:
    request = {
        **CALM_REQUEST,
        "taste": {**CALM_REQUEST["taste"], "exclude_artists": ["lo-fi artist 0"]},
    }

    body = client_with(app, FakeCatalogue()).post(URL, json=request).json()

    assert all(t["track"]["artists"][0]["name"] != "lo-fi artist 0" for t in body["tracks"])


def test_mood_only_request_still_curates(app: FastAPI) -> None:
    body = (
        client_with(app, FakeCatalogue())
        .post(URL, json={"mood": {"text": "heading to the gym"}})
        .json()
    )

    assert body["mood"]["mode"] == "energy"
    assert len(body["tracks"]) == 15
    assert body["searches"] == 4


def test_thin_results_come_with_a_note(app: FastAPI) -> None:
    body = (
        client_with(app, FakeCatalogue(per_genre=2))
        .post(URL, json={"mood": {"chips": ["calm"]}})
        .json()
    )

    assert len(body["tracks"]) < 15
    assert "Found" in body["note"]


@pytest.mark.parametrize(
    ("taste", "word"),
    [({"genres": ["vaporwave-ish"]}, "genre"), ({"languages": ["xx"]}, "language")],
)
def test_unknown_genres_and_languages_are_rejected(
    app: FastAPI, taste: dict[str, Any], word: str
) -> None:
    response = client_with(app, FakeCatalogue()).post(
        URL, json={"mood": {"chips": ["calm"]}, "taste": taste}
    )

    assert response.status_code == 422
    assert word in response.json()["detail"]["message"].lower()


def test_unknown_mood_chip_is_rejected(app: FastAPI) -> None:
    response = client_with(app, FakeCatalogue()).post(URL, json={"mood": {"chips": ["hangry"]}})

    assert response.status_code == 422


@pytest.mark.parametrize("size", [9, 31])
def test_playlist_size_must_be_between_10_and_30(app: FastAPI, size: int) -> None:
    response = client_with(app, FakeCatalogue()).post(
        URL, json={"mood": {"chips": ["calm"]}, "size": size}
    )

    assert response.status_code == 422


def test_spotify_not_configured_gives_503(client: TestClient) -> None:
    assert client.post(URL, json={"mood": {"chips": ["calm"]}}).status_code == 503


def test_spotify_rate_limit_gives_429(app: FastAPI) -> None:
    response = client_with(app, FakeCatalogue(error=SpotifyRateLimitError(9))).post(
        URL, json={"mood": {"chips": ["calm"]}}
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "9"


def test_curate_finishes_within_5_seconds_with_slow_spotify(app: FastAPI) -> None:  # NFR1
    client = client_with(app, FakeCatalogue(delay=0.3))  # every search takes 300 ms

    start = time.perf_counter()
    response = client.post(URL, json=CALM_REQUEST)
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 5


def test_options_list_genres_and_languages(client: TestClient) -> None:
    body = client.get(f"{URL}/options").json()

    assert any(g["id"] == "bollywood" and g["languages"] == ["hi"] for g in body["genres"])
    assert body["languages"]["mr"] == "Marathi"


def test_full_chain_with_only_the_network_faked(monkeypatch: pytest.MonkeyPatch) -> None:
    def spotify(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            return httpx2.Response(200, json={"access_token": "tok", "expires_in": 3600})
        offset = int(request.url.params["offset"])
        items = [
            {
                "id": f"t{offset + i}",
                "name": f"Track {offset + i}",
                "artists": [{"id": f"a{(offset + i) % 7}", "name": f"Artist {(offset + i) % 7}"}],
                "album": {"name": "A", "release_date": "2021-01-01", "images": []},
                "external_urls": {"spotify": "https://open.spotify.com/track/x"},
                "uri": f"spotify:track:t{offset + i}",
                "explicit": False,
                "duration_ms": 180_000,
            }
            for i in range(10)
        ]
        return httpx2.Response(200, json={"tracks": {"items": items}})

    real_client = httpx2.AsyncClient
    monkeypatch.setattr(
        "app.services.spotify_session.httpx2.AsyncClient",
        lambda **kw: real_client(transport=httpx2.MockTransport(spotify), **kw),
    )
    settings = Settings(
        _env_file=None, app_env="test", spotify_client_id="id", spotify_client_secret="s"
    )

    response = TestClient(create_app(settings)).post(URL, json={"mood": {"chips": ["calm"]}})

    assert response.status_code == 200
    assert len(response.json()["tracks"]) == 15

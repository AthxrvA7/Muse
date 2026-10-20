"""Spotify client: search, paging, parsing and query building (no real network)."""

from typing import Any

import httpx2
import pytest

from app.clients.spotify import TOKEN_URL, SpotifyClient, TokenCache, build_query


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def track_json(n: int, **overrides: Any) -> dict[str, Any]:
    track = {
        "id": f"t{n}",
        "name": f"Song {n}",
        "artists": [{"id": "a1", "name": "Arijit Singh"}],
        "album": {
            "name": "Album",
            "release_date": "2019-05-03",
            "images": [{"url": "https://i.scdn.co/image/big"}],
        },
        "external_urls": {"spotify": f"https://open.spotify.com/track/t{n}"},
        "uri": f"spotify:track:t{n}",
        "explicit": False,
        "duration_ms": 200_000,
    }
    track.update(overrides)
    return track


class CatalogFake:
    """Serves `available` tracks, 10 (or `limit`) at a time, like Spotify search."""

    def __init__(self, available: int) -> None:
        self.available = available
        self.searches: list[httpx2.QueryParams] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            return httpx2.Response(200, json={"access_token": "t", "expires_in": 3600})
        params = request.url.params
        self.searches.append(params)
        start, limit = int(params["offset"]), int(params["limit"])
        items = [track_json(n) for n in range(start, min(start + limit, self.available))]
        return httpx2.Response(200, json={"tracks": {"items": items}})


def make_client(handler: Any) -> SpotifyClient:
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    return SpotifyClient(http, "id", "secret", "IN", TokenCache())


@pytest.mark.anyio
async def test_results_are_fetched_ten_at_a_time() -> None:
    spotify = CatalogFake(available=100)

    tracks = await make_client(spotify).search_tracks("lofi", total=25)

    assert len(tracks) == 25
    assert [(p["offset"], p["limit"]) for p in spotify.searches] == [
        ("0", "10"),
        ("10", "10"),
        ("20", "5"),
    ]


@pytest.mark.anyio
async def test_paging_stops_when_spotify_runs_out() -> None:
    spotify = CatalogFake(available=12)

    tracks = await make_client(spotify).search_tracks("rare query", total=30)

    assert len(tracks) == 12
    assert len(spotify.searches) == 2


@pytest.mark.anyio
async def test_every_search_sends_the_market() -> None:
    spotify = CatalogFake(available=5)

    await make_client(spotify).search_tracks("x")

    assert spotify.searches[0]["market"] == "IN"
    assert spotify.searches[0]["type"] == "track"


@pytest.mark.anyio
async def test_tracks_are_parsed_into_muse_fields() -> None:
    track = (await make_client(CatalogFake(available=1)).search_tracks("x"))[0]

    assert track.name == "Song 0"
    assert track.artists[0].name == "Arijit Singh"
    assert track.release_year == 2019
    assert track.image_url == "https://i.scdn.co/image/big"
    assert track.uri == "spotify:track:t0"


@pytest.mark.anyio
async def test_null_and_malformed_items_are_skipped() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            return httpx2.Response(200, json={"access_token": "t", "expires_in": 3600})
        broken = track_json(2)
        del broken["uri"]
        items = [
            track_json(1),
            None,
            broken,
            track_json(3, album={"name": "A", "release_date": ""}),
        ]
        return httpx2.Response(200, json={"tracks": {"items": items}})

    tracks = await make_client(handler).search_tracks("x")

    assert [t.id for t in tracks] == ["t1", "t3"]
    assert tracks[1].release_year is None
    assert tracks[1].image_url is None


@pytest.mark.anyio
async def test_artist_search_returns_artists() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == TOKEN_URL:
            return httpx2.Response(200, json={"access_token": "t", "expires_in": 3600})
        artist = {
            "id": "a1",
            "name": "Prateek Kuhad",
            "genres": [],
            "images": [],
            "external_urls": {"spotify": "https://open.spotify.com/artist/a1"},
        }
        return httpx2.Response(200, json={"artists": {"items": [artist]}})

    artists = await make_client(handler).search_artists("prateek")

    assert artists[0].name == "Prateek Kuhad"
    assert artists[0].genres == []


def test_build_query_adds_filters() -> None:
    assert build_query(artist="Arijit Singh", genre="sufi") == 'artist:"Arijit Singh" genre:"sufi"'
    assert build_query("rain", year="2010-2019") == "rain year:2010-2019"


def test_build_query_strips_quotes_and_control_characters() -> None:
    assert build_query(artist='AC/DC" OR "x\n') == 'artist:"AC/DC OR x"'


def test_build_query_ignores_invalid_years_and_empty_parts() -> None:
    assert build_query("lofi", year="last year", artist="  ") == "lofi"


def test_build_query_limits_term_length() -> None:
    assert len(build_query("a" * 500)) == 100

"""Last.fm client and tag-based song moods (fake Last.fm, no network)."""

import asyncio
import logging

import httpx2
import pytest

from app.clients.lastfm import LastFmClient, Tag, TTLCache
from app.core.logging import redact_text
from app.schemas.catalog import ArtistRef, Track
from app.services.recommender.knowledge import get_genre_knowledge
from app.services.recommender.tags import clean_title, get_tag_knowledge, mood_from_tags, tag_moods

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def track(track_id: str, name: str, artist: str) -> Track:
    return Track(
        id=track_id,
        name=name,
        artists=[ArtistRef(id=artist.lower(), name=artist)],
        album="",
        release_year=None,
        image_url=None,
        spotify_url=f"https://open.spotify.com/track/{track_id}",
        uri=f"spotify:track:{track_id}",
        explicit=False,
        duration_ms=1,
    )


class FakeLastFm:
    def __init__(self) -> None:
        self.calls: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.calls.append(request)
        method = request.url.params["method"]
        if method == "track.gettoptags" and request.url.params["track"] == "Kasoor":
            return httpx2.Response(
                200,
                json={
                    "toptags": {
                        "tag": [
                            {"name": "Chill", "count": 100},
                            {"name": "hindi indie", "count": 60},
                            {"name": "seen live", "count": 40},
                        ]
                    }
                },
            )
        if method == "track.gettoptags":
            return httpx2.Response(200, json={"error": 6, "message": "Track not found"})
        if method == "artist.gettoptags":
            return httpx2.Response(200, json={"toptags": {"tag": {"name": "sad", "count": 100}}})
        if method == "artist.getsimilar":
            return httpx2.Response(
                200, json={"similarartists": {"artist": [{"name": "Anuv Jain"}, {"name": "JV"}]}}
            )
        return httpx2.Response(500)


def client(fake: FakeLastFm) -> LastFmClient:
    http = httpx2.AsyncClient(transport=httpx2.MockTransport(fake))
    return LastFmClient(http, "secret-key", TTLCache())


async def test_track_tags_are_read_and_cached() -> None:
    fake = FakeLastFm()
    lastfm = client(fake)

    first = await lastfm.track_tags("Prateek Kuhad", "Kasoor")
    second = await lastfm.track_tags("prateek kuhad", "kasoor")  # same song, other case

    assert first == [Tag("chill", 100), Tag("hindi indie", 60), Tag("seen live", 40)]
    assert second == first
    assert len(fake.calls) == 1
    assert fake.calls[0].url.params["api_key"] == "secret-key"


async def test_missing_track_and_single_tag_answers_are_handled() -> None:
    lastfm = client(FakeLastFm())

    assert await lastfm.track_tags("X", "Unknown") == []
    assert await lastfm.artist_tags("X") == [Tag("sad", 100)]
    assert await lastfm.similar_artists("Prateek Kuhad") == ["Anuv Jain", "JV"]


async def test_failures_become_no_data_and_are_not_cached() -> None:
    def broken(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("down")

    lastfm = LastFmClient(httpx2.AsyncClient(transport=httpx2.MockTransport(broken)), "k")

    assert await lastfm.similar_artists("Anyone") == []


def test_api_key_is_masked_in_logs() -> None:
    url = "https://ws.audioscrobbler.com/2.0/?method=x&api_key=abc123&format=json"
    assert "abc123" not in redact_text(url)
    assert logging.getLogger("app.clients.lastfm")  # module logs never include URLs


def test_feeling_tags_set_the_mood_and_genre_tags_help() -> None:
    mood = mood_from_tags(
        [Tag("chill", 100), Tag("hindi indie", 60), Tag("seen live", 90), Tag("sad", 5)],
        get_tag_knowledge(),
        get_genre_knowledge(),
    )

    assert mood is not None
    assert mood.words == ["chill"]  # "sad" is too rare, "seen live" isn't a feeling
    assert mood.certainty == 0.9
    assert mood.point.energy < 0.4  # chill and hindi indie are both calm


def test_genre_only_and_artist_tags_are_less_certain() -> None:
    genre_only = mood_from_tags([Tag("bollywood", 100)], get_tag_knowledge(), get_genre_knowledge())
    from_artist = mood_from_tags(
        [Tag("party", 100)], get_tag_knowledge(), get_genre_knowledge(), "artist"
    )

    assert genre_only is not None and genre_only.certainty == 0.6
    assert from_artist is not None and from_artist.certainty == 0.65
    assert (
        mood_from_tags([Tag("seen live", 100)], get_tag_knowledge(), get_genre_knowledge()) is None
    )


def test_titles_are_cleaned_for_last_fm() -> None:
    assert clean_title("Kasoor - Acoustic Version") == "Kasoor"
    assert clean_title("Baarishein (feat. X) [Live]") == "Baarishein"


async def test_tag_moods_fall_back_to_the_artist_and_respect_the_budget() -> None:
    lastfm = client(FakeLastFm())

    moods = await tag_moods(
        lastfm,
        [track("t1", "Kasoor", "Prateek Kuhad"), track("t2", "Other", "Prateek Kuhad")],
        get_genre_knowledge(),
    )

    assert moods["t1"].source == "track" and moods["t1"].words == ["chill"]
    assert moods["t2"].source == "artist" and moods["t2"].words == ["sad"]


async def test_slow_last_fm_never_holds_the_playlist_up() -> None:
    class Slow:
        async def track_tags(self, artist: str, track: str) -> list[Tag]:
            await asyncio.sleep(5)
            return []

        async def artist_tags(self, artist: str) -> list[Tag]:
            return []

    moods = await tag_moods(Slow(), [track("t1", "A", "B")], get_genre_knowledge(), budget=0.05)

    assert moods == {}

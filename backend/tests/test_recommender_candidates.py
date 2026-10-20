"""Candidate search: parallel searches, fallback, merging and failure handling."""

import pytest

from app.clients.spotify import SpotifyRateLimitError, SpotifyUnavailableError
from app.schemas.catalog import Track
from app.services.recommender.candidates import gather_candidates
from app.services.recommender.planner import SearchPlan
from tests.recommender_fixtures import track


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeSearcher:
    def __init__(self, results: dict[str, list[Track] | Exception]) -> None:
        self.results = results
        self.queries: list[str] = []

    async def search_tracks(self, query: str, total: int = 10) -> list[Track]:
        self.queries.append(query)
        result = self.results.get(query, [])
        if isinstance(result, Exception):
            raise result
        return list(result)


ARTIST = SearchPlan("artist", "Prateek Kuhad", "favourite_artist", 'artist:"Prateek Kuhad"')
GENRE = SearchPlan("genre", "indie folk", "favourite_genre", 'genre:"indie folk"', "indie folk")


@pytest.mark.anyio
async def test_tracks_found_by_two_searches_are_merged_with_both_sources() -> None:
    shared = track("t1", "Prateek Kuhad")
    spotify = FakeSearcher({ARTIST.query: [shared, track("t2")], GENRE.query: [shared] * 6})

    candidates = await gather_candidates(spotify, [ARTIST, GENRE])

    by_id = {c.track.id: c for c in candidates}
    assert set(by_id) == {"t1", "t2"}
    assert [s.reason for s in by_id["t1"].sources] == ["favourite_artist", "favourite_genre"]


@pytest.mark.anyio
async def test_thin_genre_results_fall_back_to_keywords() -> None:
    spotify = FakeSearcher({GENRE.query: [track("g1")], "indie folk": [track("g1"), track("k1")]})

    candidates = await gather_candidates(spotify, [GENRE])

    assert spotify.queries == ['genre:"indie folk"', "indie folk"]
    assert [c.track.id for c in candidates] == ["g1", "k1"]


@pytest.mark.anyio
async def test_one_failed_search_does_not_sink_the_playlist() -> None:
    spotify = FakeSearcher(
        {ARTIST.query: SpotifyUnavailableError("down"), GENRE.query: [track("g")] * 5}
    )

    candidates = await gather_candidates(spotify, [ARTIST, GENRE])

    assert [c.track.id for c in candidates] == ["g"]


@pytest.mark.anyio
async def test_all_searches_failing_means_spotify_is_unavailable() -> None:
    down = SpotifyUnavailableError("down")
    spotify = FakeSearcher({ARTIST.query: down, GENRE.query: down})

    with pytest.raises(SpotifyUnavailableError):
        await gather_candidates(spotify, [ARTIST, GENRE])


@pytest.mark.anyio
async def test_a_rate_limit_stops_everything() -> None:
    spotify = FakeSearcher({ARTIST.query: SpotifyRateLimitError(10), GENRE.query: [track("g")] * 5})

    with pytest.raises(SpotifyRateLimitError):
        await gather_candidates(spotify, [ARTIST, GENRE])

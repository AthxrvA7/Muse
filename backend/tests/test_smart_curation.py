"""Smarter curation: the user's own top tracks, Last.fm moods and similar artists,
the familiar/new mix, and never the same playlist twice (all fakes, no network)."""

import random
import re

import pytest
from fastapi.testclient import TestClient

from app.api.deps import personal_context
from app.clients.lastfm import Tag
from app.clients.spotify import SpotifyUnavailableError
from app.core.config import Settings
from app.main import create_app
from app.schemas.catalog import Track
from app.schemas.curate import CurateRequest
from app.services.curate import CurateService, Personal, get_curate_service
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.vocabulary import load_vocabulary
from app.services.recommender.knowledge import load_genre_knowledge
from tests.recommender_fixtures import track

pytestmark = pytest.mark.anyio
KB = load_genre_knowledge()
SAD = [Tag("sad", 100), Tag("melancholy", 60)]
PARTY = [Tag("party", 100), Tag("dance", 70)]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class Catalogue:
    """artist:"X" -> 8 songs by X; genre searches -> 12 songs by 6 genre artists."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search_tracks(self, query: str, total: int = 10) -> list[Track]:
        self.queries.append(query)
        if m := re.fullmatch(r'artist:"(.+)"', query):
            name = m.group(1)
            return [track(f"{name[:3]}{i}", name, f"{name} song {i}") for i in range(8)]
        if m := re.fullmatch(r'genre:"(.+)"', query):
            g = m.group(1)
            return [track(f"g{g[:3]}{i}", f"{g} artist {i % 6}") for i in range(12)]
        return []


class LastFm:
    """Sad tags for songs whose title says 'sad', party tags for the rest."""

    def __init__(self, similar: list[str] | None = None) -> None:
        self.similar = similar if similar is not None else ["Anuv Jain", "Prateek Kuhad"]

    async def similar_artists(self, artist: str, limit: int = 8) -> list[str]:
        return self.similar[:limit]

    async def track_tags(self, artist: str, track: str) -> list[Tag]:
        return SAD if "sad" in track.lower() else PARTY

    async def artist_tags(self, artist: str) -> list[Tag]:
        return []


class TopTracks:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def top_tracks(self, time_range: str) -> list[Track]:
        if self.error:
            raise self.error
        if time_range == "short_term":
            return [track(f"mine{i}", f"Fav {i}", f"My sad song {i}") for i in range(6)]
        return [track(f"old{i}", f"Old {i}", f"Old party song {i}") for i in range(6)]


class Recent:
    def __init__(self, ids: list[str] | None = None) -> None:
        self.ids = ids or []
        self.remembered: list[list[str]] = []

    async def get(self, user_id: str) -> list[str]:
        return self.ids

    async def remember(self, user_id: str, track_ids: list[str]) -> None:
        self.remembered.append(track_ids)


def service(lastfm: LastFm | None = None, catalogue: Catalogue | None = None) -> CurateService:
    return CurateService(
        catalogue or Catalogue(),
        MoodAnalyzer(load_vocabulary()),
        KB,
        lastfm if lastfm is not None else LastFm(),
    )


def request(**extra: object) -> CurateRequest:
    body: dict[str, object] = {
        "mood": {"chips": ["low", "lonely"]},
        "taste": {"artists": ["Arijit Singh"], "genres": ["indie folk"]},
        "size": 12,
    }
    body.update(extra)
    return CurateRequest.model_validate(body)


async def test_songs_the_user_plays_are_mixed_in_and_explained() -> None:
    preview = await service().preview(request(), Personal("u1", TopTracks(), Recent()))

    known = [t for t in preview.tracks if t.track.id.startswith(("mine", "old"))]
    assert preview.personal is True
    assert known, "the user's own top tracks should appear"
    assert all(t.known for t in known)
    recent_song = next(t for t in preview.tracks if t.track.id.startswith("mine"))
    assert "playing it a lot lately" in recent_song.reason


async def test_last_fm_tags_pick_which_of_my_songs_fit_the_mood() -> None:
    preview = await service().preview(
        request(familiarity=1.0, taste={"artists": []}), Personal("u1", TopTracks())
    )

    ids = [t.track.id for t in preview.tracks]
    sad_ranks = [ids.index(i) for i in ids if i.startswith("mine")]
    party_ranks = [ids.index(i) for i in ids if i.startswith("old")]
    assert preview.mood_data == "lastfm"
    assert max(sad_ranks) < min(party_ranks)  # sad songs first for a low, lonely mood
    first = preview.tracks[0]
    assert first.tags == ["sad", "melancholy"]
    assert "listeners tag it 'sad' and 'melancholy'" in first.reason


async def test_familiarity_sets_the_share_of_known_songs() -> None:
    mostly_known = await service().preview(request(familiarity=0.9), Personal("u", TopTracks()))
    mostly_new = await service().preview(request(familiarity=0.1), Personal("u", TopTracks()))

    def known(p: object) -> int:
        return sum(t.known for t in p.tracks)  # type: ignore[attr-defined]

    assert known(mostly_known) >= 10
    assert known(mostly_new) <= 2
    assert mostly_new.familiarity == 0.1


async def test_mode_sets_the_default_familiarity() -> None:
    preview = await service().preview(
        request(mood={"chips": ["low"], "mode": "discovery"}), Personal("u", TopTracks())
    )
    assert preview.familiarity == 0.3


async def test_similar_artists_are_searched_and_named_in_the_reason() -> None:
    catalogue = Catalogue()

    preview = await service(LastFm(similar=["Anuv Jain"]), catalogue).preview(
        request(familiarity=0.0)
    )

    assert 'artist:"Anuv Jain"' in catalogue.queries
    assert preview.similar_artists == ["Anuv Jain"]
    anuv = next(t for t in preview.tracks if t.track.artists[0].name == "Anuv Jain")
    assert "similar to Arijit Singh" in anuv.reason


async def test_favourites_and_excluded_artists_are_not_offered_as_similar() -> None:
    preview = await service(LastFm(similar=["Arijit Singh", "Blocked", "JV"])).preview(
        request(taste={"artists": ["Arijit Singh"], "exclude_artists": ["Blocked"]})
    )
    assert preview.similar_artists == ["JV"]


async def test_give_me_another_leaves_out_the_last_playlist() -> None:
    first = await service().preview(request(), Personal("u", TopTracks()))
    first_ids = [t.track.id for t in first.tracks]

    second = await service().preview(
        request(exclude_track_ids=first_ids), Personal("u", TopTracks())
    )

    assert not set(first_ids) & {t.track.id for t in second.tracks}


async def test_recent_picks_are_remembered_and_less_likely_next_time() -> None:
    recent = Recent()
    first = await service().preview(request(), Personal("u", TopTracks(), recent))
    assert recent.remembered == [[t.track.id for t in first.tracks]]

    again = await service().preview(
        request(), Personal("u", TopTracks(), Recent(ids=recent.remembered[0]))
    )
    repeated = {t.track.id for t in again.tracks} & set(recent.remembered[0])
    assert len(repeated) < len(first.tracks)


async def test_variety_changes_the_order_of_equally_good_songs() -> None:
    def varied(seed: int) -> CurateService:
        return CurateService(
            Catalogue(),
            MoodAnalyzer(load_vocabulary()),
            KB,
            LastFm(),
            0.04,
            random.Random(seed),  # noqa: S311
        )

    playlists = {
        tuple(t.track.id for t in (await varied(seed).preview(request())).tracks)
        for seed in range(5)
    }
    assert len(playlists) > 1


async def test_spotify_or_last_fm_trouble_still_gives_a_playlist() -> None:
    class Broken(LastFm):
        async def track_tags(self, artist: str, track: str) -> list[Tag]:
            raise RuntimeError("down")

        async def similar_artists(self, artist: str, limit: int = 8) -> list[str]:
            raise RuntimeError("down")

    preview = await service(Broken()).preview(
        request(), Personal("u", TopTracks(error=SpotifyUnavailableError("x")))
    )

    assert len(preview.tracks) == 12
    assert preview.personal is False
    assert preview.mood_data == "estimated"


def test_curate_api_uses_the_logged_in_users_music() -> None:
    app = create_app(
        Settings(_env_file=None, app_env="test", spotify_client_id="i", spotify_client_secret="s")
    )
    app.dependency_overrides[get_curate_service] = lambda: service()
    app.dependency_overrides[personal_context] = lambda: Personal("u", TopTracks(), Recent())

    response = TestClient(app).post(
        "/api/v1/curate",
        json={
            "mood": {"chips": ["low"]},
            "taste": {"artists": ["Arijit Singh"]},
            "familiarity": 0.5,
            "exclude_track_ids": ["mine0"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["personal"] is True
    assert "mine0" not in [t["track"]["id"] for t in body["tracks"]]
    assert {"known", "tags"} <= set(body["tracks"][0])


def test_bad_familiarity_and_track_ids_are_rejected() -> None:
    settings = Settings(
        _env_file=None, app_env="test", spotify_client_id="i", spotify_client_secret="s"
    )
    client = TestClient(create_app(settings))
    for extra in ({"familiarity": 1.5}, {"exclude_track_ids": ["not an id!"]}):
        body = {"mood": {"chips": ["low"]}, **extra}
        assert client.post("/api/v1/curate", json=body).status_code == 422

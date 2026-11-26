"""Coherent playlists: one language, one genre with close neighbours, and tempo (fakes only)."""

import asyncio

import httpx2
import pytest

from app.clients.deezer import DeezerClient, DeezerMatch
from app.clients.lastfm import Tag, TTLCache
from app.schemas.curate import CurateRequest
from app.services.curate import CurateService
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.vocabulary import load_vocabulary
from app.services.recommender.candidates import Candidate
from app.services.recommender.focus import add_tempo, focus_playlist, tempo_of
from app.services.recommender.knowledge import load_genre_knowledge
from app.services.recommender.scoring import ScoredTrack
from app.services.recommender.tags import script_language, tag_genre, tag_language
from tests.recommender_fixtures import track

pytestmark = pytest.mark.anyio
KB = load_genre_knowledge()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def item(
    track_id: str, score: float, language: str | None, genre: str | None, artist: str = ""
) -> ScoredTrack:
    return ScoredTrack(
        candidate=Candidate(track(track_id, artist or f"artist {track_id}")),
        mood_fit=0.5,
        taste_fit=0.5,
        score=score,
        mood_source=None,
        favourite_artist=None,
        taste_reason=None,
        genre=genre,
        language=language,
    )


# ---------------------------------------------------------------- knowledge


def test_genre_coherence_follows_families() -> None:
    assert KB.coherence("bollywood", "bollywood") == 1.0
    assert KB.coherence("filmi", "bollywood") == 0.85  # same family
    assert KB.coherence("sufi", "bollywood") == 0.55  # related family
    assert KB.coherence("metal", "bollywood") == 0.0  # unrelated
    assert KB.coherence(None, "bollywood") == 0.5  # unknown


def test_language_and_genre_come_from_tags_and_script() -> None:
    arijit = [Tag("bollywood", 100), Tag("hindi", 80), Tag("pop", 30), Tag("romantic", 50)]
    assert tag_genre(arijit, KB) == "bollywood"
    assert tag_language(arijit, KB) == "hi"
    assert tag_language([Tag("indie rock", 100)], KB) == "en"  # through the genre
    assert tag_language([Tag("seen live", 100)], KB) is None
    assert script_language("तुम ही हो") == "hi"
    assert script_language("봄날") == "ko"
    assert script_language("Kasoor") is None


# ---------------------------------------------------------------- focus


def test_auto_language_keeps_the_main_language_and_drops_others() -> None:
    items = [item(f"h{i}", 0.8, "hi", "bollywood") for i in range(12)]
    items += [item(f"e{i}", 0.7, "en", "pop") for i in range(4)]
    items += [item("lofi", 0.6, None, "lo-fi"), item("x", 0.6, None, None)]

    pool, focus = focus_playlist(items, 10, KB)

    ids = {s.candidate.track.id for s in pool}
    assert focus.language == "hi"
    assert not any(i.startswith("e") for i in ids)
    assert "x" not in ids  # unknown language: never used, so nothing can slip in
    assert "lofi" not in ids  # instrumental is allowed language-wise, but it's off-genre here


def test_one_taste_language_is_used_when_there_are_songs_in_it() -> None:
    items = [item(f"e{i}", 0.9, "en", "pop") for i in range(12)]
    items += [item(f"h{i}", 0.6, "hi", "bollywood") for i in range(6)]

    _, focus = focus_playlist(items, 10, KB, preferred=["hi"])
    _, none_preferred = focus_playlist(items, 10, KB)

    assert focus.language == "hi"
    assert none_preferred.language == "en"


def test_a_chosen_language_or_mix_is_respected() -> None:
    items = [item(f"h{i}", 0.8, "hi", "bollywood") for i in range(12)]
    items += [item(f"e{i}", 0.7, "en", "pop") for i in range(12)]

    english, focus = focus_playlist(items, 10, KB, language="en")
    mixed, mixed_focus = focus_playlist(
        [item(f"h{i}", 0.8, "hi", "bollywood") for i in range(3)]
        + [item(f"e{i}", 0.7, "en", "pop") for i in range(3)],
        5,
        KB,
        language="mix",
    )

    assert focus.language == "en"
    assert all(s.language == "en" for s in english)
    assert mixed_focus.language is None
    assert len(mixed) == 6


def test_too_few_songs_in_a_language_never_lets_others_in() -> None:
    items = [item("h1", 0.8, "hi", "bollywood")] + [
        item(f"e{i}", 0.7, "en", "pop") for i in range(12)
    ]

    pool, _ = focus_playlist(items, 10, KB, language="hi")

    assert [s.candidate.track.id for s in pool] == ["h1"]  # short, but never mixed


def test_instrumental_songs_can_join_any_language() -> None:
    items = [item(f"h{i}", 0.8, "hi", "lo-fi") for i in range(3)] + [
        item("beat", 0.7, None, "lo-fi")
    ]

    pool, _ = focus_playlist(items, 3, KB, language="hi")

    assert "beat" in {s.candidate.track.id for s in pool}


def test_one_genre_leads_and_unrelated_genres_are_left_out() -> None:
    items = [item(f"b{i}", 0.8, "hi", "bollywood") for i in range(10)]
    items += [item(f"f{i}", 0.7, "hi", "filmi") for i in range(6)]
    items += [item(f"s{i}", 0.7, "hi", "sufi") for i in range(3)]
    items += [item(f"m{i}", 0.75, "hi", "desi hip hop") for i in range(3)]

    pool, focus = focus_playlist(items, 10, KB)

    genres = {s.genre for s in pool}
    assert focus.genre == "bollywood"
    assert "desi hip hop" not in genres  # unrelated family, and there are enough others
    assert {"filmi", "sufi"} <= genres  # same and related families stay
    best = max(pool, key=lambda s: s.score)
    assert best.genre == "bollywood"


def test_a_requested_genre_becomes_the_anchor() -> None:
    items = [item(f"b{i}", 0.8, "hi", "bollywood") for i in range(10)]
    items += [item(f"s{i}", 0.6, "hi", "sufi") for i in range(10)]

    pool, focus = focus_playlist(items, 10, KB, genre="sufi")

    assert focus.genre == "sufi"
    assert max(pool, key=lambda s: s.score).genre == "sufi"


# ---------------------------------------------------------------- tempo


class FakeTempo:
    def __init__(self, bpms: dict[str, float | None], delay: float = 0.0) -> None:
        self.bpms, self.delay = bpms, delay

    async def match(self, isrc: str | None, artist: str, title: str) -> DeezerMatch:
        await asyncio.sleep(self.delay)
        bpm = self.bpms.get(artist)
        return DeezerMatch(deezer_id=1000 + len(artist) if bpm else None, bpm=bpm)


def test_tempo_classes() -> None:
    assert (tempo_of(80), tempo_of(110), tempo_of(140)) == ("slow", "medium", "fast")


async def test_tempo_is_added_and_nudges_scores_towards_the_mood() -> None:
    slow, fast, unknown = (
        item("a", 0.6, "hi", "bollywood", "Slow One"),
        item("b", 0.6, "hi", "bollywood", "Fast One"),
        item("c", 0.6, "hi", "bollywood", "Nobody"),
    )

    await add_tempo(
        FakeTempo({"Slow One": 78.0, "Fast One": 150.0}), [slow, fast, unknown], "slow", 5
    )

    assert (slow.bpm, slow.tempo) == (78.0, "slow")
    assert fast.tempo == "fast"
    assert unknown.bpm is None
    assert slow.score > unknown.score > fast.score


async def test_slow_tempo_lookups_never_hold_the_playlist_up() -> None:
    one = item("a", 0.6, "hi", "bollywood", "Slow One")
    await add_tempo(FakeTempo({"Slow One": 78.0}, delay=5), [one], "slow", 5, budget=0.05)
    assert one.bpm is None


async def test_deezer_finds_bpm_by_isrc_then_by_search_and_caches() -> None:
    calls: list[str] = []

    def deezer(request: httpx2.Request) -> httpx2.Response:
        calls.append(str(request.url))
        path = request.url.path
        if path == "/track/isrc:INX001":
            return httpx2.Response(200, json={"id": 1, "bpm": 92.4})
        if path.startswith("/track/isrc:"):
            return httpx2.Response(200, json={"error": {"type": "DataException", "code": 800}})
        if path == "/search":
            return httpx2.Response(200, json={"data": [{"id": 77}]})
        if path == "/track/77":
            return httpx2.Response(200, json={"id": 77, "bpm": 0})  # Deezer doesn't know
        return httpx2.Response(404)

    client = DeezerClient(httpx2.AsyncClient(transport=httpx2.MockTransport(deezer)), TTLCache())

    assert await client.bpm("INX001", "Arijit Singh", "Tum Hi Ho") == 92.4
    assert await client.bpm("INX001", "Arijit Singh", "Tum Hi Ho") == 92.4
    assert await client.bpm("NOPE", "Someone", "Song") is None
    assert await client.bpm("NOPE", "Someone", "Song") is None
    assert len(calls) == 4  # isrc hit once; miss = isrc + search + track, then cached


# ---------------------------------------------------------------- end to end


class Catalogue:
    async def search_tracks(self, query: str, total: int = 10) -> list:  # type: ignore[type-arg]
        if 'artist:"Arijit Singh"' in query:
            return [track(f"h{i}", "Arijit Singh", f"Hindi song {i}") for i in range(8)]
        if 'artist:"Taylor Swift"' in query:
            return [track(f"e{i}", "Taylor Swift", f"English song {i}") for i in range(8)]
        return []


class LastFm:
    async def similar_artists(self, artist: str, limit: int = 8) -> list[str]:
        return []

    async def track_tags(self, artist: str, track: str) -> list[Tag]:
        return []

    async def artist_tags(self, artist: str) -> list[Tag]:
        if artist == "Arijit Singh":
            return [Tag("bollywood", 100), Tag("hindi", 80), Tag("romantic", 40)]
        return [Tag("pop", 100), Tag("english", 20), Tag("happy", 40)]


async def test_curated_playlist_stays_in_one_language_and_shows_tempo() -> None:
    service = CurateService(
        Catalogue(),
        MoodAnalyzer(load_vocabulary()),
        KB,
        LastFm(),
        deezer=FakeTempo({"Arijit Singh": 84.0, "Taylor Swift": 120.0}),
    )
    request = CurateRequest.model_validate(
        {
            "mood": {"chips": ["calm"]},
            "taste": {"artists": ["Arijit Singh", "Taylor Swift"]},
            "size": 10,
            "language": "hi",
        }
    )

    preview = await service.preview(request)

    assert preview.language == "hi"
    assert preview.genre == "bollywood"
    hindi = [t for t in preview.tracks if t.language == "hi"]
    assert hindi and hindi[0].genre == "Bollywood"
    assert hindi[0].bpm == 84.0 and hindi[0].tempo == "slow"
    assert all(t.language == "hi" for t in preview.tracks[: len(hindi)])


async def test_unknown_language_or_genre_choice_is_rejected() -> None:
    from app.services.curate import UnknownTasteError

    service = CurateService(Catalogue(), MoodAnalyzer(load_vocabulary()), KB)
    for extra in ({"language": "xx"}, {"genre": "no such genre"}):
        request = CurateRequest.model_validate({"mood": {"chips": ["calm"]}, **extra})
        with pytest.raises(UnknownTasteError):
            await service.preview(request)


# ---------------------------------------------------------------- language detection


def test_romanised_titles_give_their_language_away() -> None:
    from app.services.recommender.tags import title_language

    assert title_language("Tum Hi Ho") == "hi"
    assert title_language("Channa Mereya - From Ae Dil Hai Mushkil") == "hi"
    assert title_language("Tenu Leke") == "pa"
    assert title_language("Shape of You") == "en"
    assert title_language("Kasoor") is None  # not enough to tell


def test_language_needs_a_clear_winner() -> None:
    from app.services.recommender.tags import decide_language

    hindi_artist = [Tag("bollywood", 100), Tag("hindi", 70)]
    song = track("t", "Arijit Singh", "Perfect")  # an English-looking title...

    assert decide_language(song, [], hindi_artist, KB) == "hi"  # ...the artist wins
    assert decide_language(track("t", "X", "Kasoor"), [], [], KB) is None
    assert decide_language(track("t", "X", "Kasoor"), [], [], KB, hint="hi") == "hi"


def test_an_artists_known_language_and_genre_fill_their_other_songs() -> None:
    from app.services.curate import _share_by_artist

    known = item("a", 0.6, "hi", "bollywood", "Arijit Singh")
    unknown = item("b", 0.6, None, None, "Arijit Singh")
    known.candidate.track.artists[0].id = unknown.candidate.track.artists[0].id = "arijit"

    _share_by_artist([known, unknown])

    assert (unknown.language, unknown.genre) == ("hi", "bollywood")


async def test_coverage_says_how_much_muse_knew() -> None:
    service = CurateService(
        Catalogue(), MoodAnalyzer(load_vocabulary()), KB, LastFm(), deezer=FakeTempo({})
    )
    request = CurateRequest.model_validate(
        {"mood": {"chips": ["calm"]}, "taste": {"artists": ["Arijit Singh"]}, "size": 10}
    )

    preview = await service.preview(request)

    assert preview.coverage.candidates == 8
    assert preview.coverage.with_language == 8
    assert preview.coverage.with_genre == 8
    assert preview.coverage.with_tempo == 0


async def test_too_few_songs_in_the_language_triggers_more_searches_in_it() -> None:
    class Thin:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search_tracks(self, query: str, total: int = 10) -> list:  # type: ignore[type-arg]
            self.queries.append(query)
            if 'artist:"Taylor Swift"' in query:
                return [track(f"e{i}", "Taylor Swift", f"English song {i}") for i in range(8)]
            if 'genre:"bollywood"' in query or 'genre:"filmi"' in query:
                g = "b" if "bollywood" in query else "f"
                return [track(f"{g}{i}", f"Film singer {g}{i % 4}", f"Song {i}") for i in range(10)]
            return []

    catalogue = Thin()
    service = CurateService(catalogue, MoodAnalyzer(load_vocabulary()), KB)
    request = CurateRequest.model_validate(
        {
            "mood": {"chips": ["calm"]},
            "taste": {"artists": ["Taylor Swift"]},
            "size": 10,
            "language": "hi",
        }
    )

    preview = await service.preview(request)

    assert any("bollywood" in q for q in catalogue.queries)  # it went looking for Hindi songs
    assert preview.language == "hi"
    assert preview.tracks and all(t.language == "hi" for t in preview.tracks)


# ---------------------------------------------------------------- previews


def _deezer(handler: object) -> DeezerClient:
    return DeezerClient(httpx2.AsyncClient(transport=httpx2.MockTransport(handler)), TTLCache())


async def test_a_fresh_preview_link_is_minted_and_reused_only_until_it_nearly_expires() -> None:
    import time

    calls: list[str] = []
    expires = int(time.time()) + 900  # Deezer signs links for about 15 minutes

    def deezer(request: httpx2.Request) -> httpx2.Response:
        calls.append(request.url.path)
        preview = f"https://cdnt-preview.dzcdn.net/api/1/1/a/b.mp3?hdnea=exp={expires}~acl=x~hmac=y"
        return httpx2.Response(200, json={"id": 42, "preview": preview})

    client = _deezer(deezer)

    first = await client.preview_url(42)
    second = await client.preview_url(42)

    assert first and first.startswith("https://cdnt-preview.dzcdn.net/")
    assert second == first
    assert calls == ["/track/42"]  # reused while still valid


def test_preview_links_live_until_a_minute_before_expiry_at_most_ten_minutes() -> None:
    from app.clients.deezer import preview_lifetime

    assert preview_lifetime("https://x.dzcdn.net/a.mp3?hdnea=exp=1000~hmac=1", now=0) == 600
    assert preview_lifetime("https://x.dzcdn.net/a.mp3?hdnea=exp=300~hmac=1", now=0) == 240
    assert preview_lifetime("https://x.dzcdn.net/a.mp3?hdnea=exp=30~hmac=1", now=0) == 0
    assert preview_lifetime("https://x.dzcdn.net/a.mp3", now=0) == 0  # no expiry: don't keep


async def test_only_deezer_cdn_links_are_ever_handed_out() -> None:
    def deezer(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"id": 7, "preview": "https://evil.example.com/a.mp3"})

    assert await _deezer(deezer).preview_url(7) is None


async def test_match_keeps_the_deezer_id_even_without_a_bpm() -> None:
    def deezer(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"id": 55, "bpm": 0})

    found = await _deezer(deezer).match("ISRC1", "A", "B")

    assert (found.deezer_id, found.bpm) == (55, None)


def test_preview_endpoint_redirects_to_a_fresh_link_and_is_never_cached() -> None:
    from fastapi.testclient import TestClient

    from app.core.config import Settings
    from app.main import create_app
    from app.services.curate import open_deezer

    class Fake:
        async def preview_url(self, deezer_id: int) -> str | None:
            return "https://cdnt-preview.dzcdn.net/x.mp3?hdnea=exp=1" if deezer_id == 42 else None

    async def fake() -> object:
        yield Fake()

    app = create_app(Settings(_env_file=None, app_env="test"))
    app.dependency_overrides[open_deezer] = fake
    client = TestClient(app)

    found = client.get("/api/v1/previews/42", follow_redirects=False)
    missing = client.get("/api/v1/previews/43", follow_redirects=False)

    assert found.status_code == 307
    assert found.headers["location"].startswith("https://cdnt-preview.dzcdn.net/")
    assert found.headers["cache-control"] == "no-store"
    assert missing.status_code == 404
    assert client.get("/api/v1/previews/0").status_code == 422


def test_the_website_may_play_deezer_audio() -> None:
    from app.core.security import _WEB_CSP

    assert "media-src 'self' https://*.dzcdn.net" in _WEB_CSP


async def test_curated_tracks_carry_their_preview_id() -> None:
    service = CurateService(
        Catalogue(),
        MoodAnalyzer(load_vocabulary()),
        KB,
        LastFm(),
        deezer=FakeTempo({"Arijit Singh": 84.0}),
    )
    request = CurateRequest.model_validate(
        {
            "mood": {"chips": ["calm"]},
            "taste": {"artists": ["Arijit Singh"]},
            "size": 10,
            "language": "hi",
        }
    )

    preview = await service.preview(request)

    assert preview.tracks and all(t.preview_id == 1012 for t in preview.tracks)

"""Curation: mood + taste -> a ranked, explained playlist preview.

    mood input --MoodAnalyzer--> MoodProfile
    favourites --Last.fm--> similar artists
    MoodProfile + taste + similar --plan_searches--> Spotify searches
    searches + the user's top tracks --> candidate tracks (familiar and new)
    candidates --Last.fm tags--> how each song feels
    candidates --keep_allowed + score_candidates--> mood_fit, taste_fit, score
    scores - recently played picks + a little variety --pick_mixed--> top N
    each pick --explain--> one-sentence reason

The mood text is never stored. For a logged-in user Muse remembers only which track
IDs it recently picked, so the next playlist isn't the same one again.
"""

import asyncio
import logging
import random
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Protocol

import httpx2
from fastapi import Depends, Request

from app.clients.deezer import DeezerClient
from app.clients.lastfm import LastFmClient
from app.clients.spotify import SpotifyClient, SpotifyError
from app.schemas.catalog import Track
from app.schemas.curate import (
    Coverage,
    CuratedTrack,
    CuratePreview,
    CurateRequest,
    GenreOption,
    Taste,
    TasteOptions,
)
from app.schemas.mood import Mode, MoodProfile
from app.services.mood import get_mood_analyzer
from app.services.mood.analyzer import MoodAnalyzer
from app.services.recommender.candidates import (
    Candidate,
    TrackSearcher,
    gather_candidates,
)
from app.services.recommender.explain import explain
from app.services.recommender.focus import (
    ROOM,
    TempoSource,
    add_tempo,
    choose_language,
    focus_playlist,
)
from app.services.recommender.knowledge import GenreKnowledge, get_genre_knowledge
from app.services.recommender.planner import SearchPlan, language_searches, plan_searches
from app.services.recommender.ranking import pick_mixed
from app.services.recommender.scoring import ScoredTrack, keep_allowed, score_candidates
from app.services.recommender.tags import (
    Hints,
    TrackProfile,
    decide_genre,
    decide_language,
    profile_tracks,
)
from app.services.spotify_session import open_spotify

logger = logging.getLogger(__name__)

# Share of songs the user already knows, per mode (the request can override it)
MODE_FAMILIARITY: dict[Mode, float] = {
    "comfort": 0.7,
    "focus": 0.6,
    "energy": 0.6,
    "discovery": 0.3,
}
TOP_RANGES = ("short_term", "medium_term")  # about 4 weeks, about 6 months
SIMILAR_FROM_FAVOURITES = 3  # ask Last.fm about this many favourite artists
SIMILAR_PER_FAVOURITE = 6
RECENT_PENALTY = 0.15  # picked for this user recently: still possible, but less likely
VARIETY = 0.04  # random nudge, so equally good songs take turns
OFF_VIBE = 0.45  # a known song whose listener-tagged feel fits worse than this...
OFF_VIBE_PENALTY = 0.15  # ...drops back, so familiar songs still match the mood


class UnknownTasteError(ValueError):
    def __init__(self, genres: list[str], languages: list[str]) -> None:
        parts = []
        if genres:
            parts.append(f"unknown genre(s): {', '.join(genres)}")
        if languages:
            parts.append(f"unknown language(s): {', '.join(languages)}")
        super().__init__("; ".join(parts).capitalize())


class LastFm(Protocol):
    async def similar_artists(self, artist: str, limit: int = ...) -> list[str]: ...
    async def track_tags(self, artist: str, track: str) -> list: ...  # type: ignore[type-arg]
    async def artist_tags(self, artist: str) -> list: ...  # type: ignore[type-arg]


class TopTracks(Protocol):
    async def top_tracks(self, time_range: str) -> list[Track]: ...


class RecentPicks(Protocol):
    async def get(self, user_id: str) -> list[str]: ...
    async def remember(self, user_id: str, track_ids: list[str]) -> None: ...


@dataclass
class Personal:
    """What Muse may use for the logged-in user (None for visitors)."""

    user_id: str
    music: TopTracks | None = None  # their Spotify top tracks, if they allowed it
    recent: RecentPicks | None = None  # what Muse picked for them recently


def taste_options(kb: GenreKnowledge) -> TasteOptions:
    return TasteOptions(
        genres=[
            GenreOption(id=gid, name=g.name, languages=g.langs) for gid, g in kb.genres.items()
        ],
        languages=kb.languages,
    )


async def find_similar(lastfm: LastFm, taste: Taste) -> dict[str, str]:
    """Artists similar to the first favourites (similar artist -> favourite), new ones only."""
    favourites = taste.artists[:SIMILAR_FROM_FAVOURITES]
    answers = await asyncio.gather(
        *(lastfm.similar_artists(name, limit=SIMILAR_PER_FAVOURITE) for name in favourites),
        return_exceptions=True,
    )
    skip = {name.lower() for name in taste.artists + taste.exclude_artists}
    similar: dict[str, str] = {}
    # Round-robin, so every favourite gets its closest matches in first
    lists = [a if isinstance(a, list) else [] for a in answers]
    for position in range(SIMILAR_PER_FAVOURITE):
        for favourite, names in zip(favourites, lists, strict=True):
            if position < len(names) and names[position].lower() not in skip:
                similar.setdefault(names[position], favourite)
                skip.add(names[position].lower())
    return similar


async def familiar_candidates(music: TopTracks) -> list[Candidate]:
    """The user's own top tracks as candidates; Spotify errors just mean none."""
    answers = await asyncio.gather(
        *(music.top_tracks(r) for r in TOP_RANGES), return_exceptions=True
    )
    found: dict[str, Candidate] = {}
    for time_range, answer in zip(TOP_RANGES, answers, strict=True):
        if isinstance(answer, SpotifyError):
            logger.warning("Could not read top tracks", extra={"time_range": time_range})
            continue
        if isinstance(answer, BaseException):
            raise answer
        plan = SearchPlan("top", time_range, "familiar", query="")
        for rank, track in enumerate(answer):
            candidate = found.setdefault(track.id, Candidate(track))
            candidate.best_rank = min(candidate.best_rank, rank)
            if plan not in candidate.sources:
                candidate.sources.append(plan)
    return list(found.values())


def _merge(searched: list[Candidate], familiar: list[Candidate]) -> list[Candidate]:
    merged = {c.track.id: c for c in searched}
    for candidate in familiar:
        if candidate.track.id in merged:
            existing = merged[candidate.track.id]
            existing.sources = candidate.sources + existing.sources
            existing.best_rank = min(existing.best_rank, candidate.best_rank)
        else:
            merged[candidate.track.id] = candidate
    return list(merged.values())


def _hints(candidate: Candidate, kb: GenreKnowledge) -> Hints:
    """What the search that found a song says: its genre, and that genre's language."""
    genre = next(
        (p.value for p in candidate.sources if p.kind == "genre" and p.value in kb.genres), None
    )
    language = kb.genres[genre].langs[0] if genre and len(kb.genres[genre].langs) == 1 else None
    return Hints(genre=genre, language=language)


def _fallback_profile(candidate: Candidate, kb: GenreKnowledge) -> TrackProfile:
    """Without Last.fm: the search that found the song, its title words and script."""
    hint = _hints(candidate, kb)
    return TrackProfile(
        mood=None,
        genre=decide_genre([], [], kb, hint.genre),
        language=decide_language(candidate.track, [], [], kb, hint.language),
    )


def _tagging_order(candidate: Candidate) -> tuple[int, int]:
    """Look up the songs most likely to be picked first (Last.fm has a time budget)."""
    reasons = {plan.reason for plan in candidate.sources}
    for position, reason in enumerate(("familiar", "favourite_artist", "similar_artist")):
        if reason in reasons:
            return position, candidate.best_rank
    return 3, candidate.best_rank


def _share_by_artist(scored: list[ScoredTrack]) -> None:
    """A song whose language or genre is unknown takes its artist's usual one."""
    by_artist: dict[str, dict[str, Counter[str]]] = {}
    for item in scored:
        artist = item.candidate.track.artists[0].id if item.candidate.track.artists else ""
        seen = by_artist.setdefault(artist, {"language": Counter(), "genre": Counter()})
        if item.language:
            seen["language"][item.language] += 1
        if item.genre:
            seen["genre"][item.genre] += 1
    for item in scored:
        artist = item.candidate.track.artists[0].id if item.candidate.track.artists else ""
        seen = by_artist.get(artist)
        if not seen:
            continue
        if not item.language and seen["language"]:
            item.language = seen["language"].most_common(1)[0][0]
        if not item.genre and seen["genre"]:
            item.genre = seen["genre"].most_common(1)[0][0]


def _planning_taste(taste: Taste, request: CurateRequest) -> Taste:
    """A chosen genre or language is searched for too, and counts as part of the taste."""
    genres = list(dict.fromkeys(([request.genre] if request.genre else []) + taste.genres))
    chosen = request.language not in ("auto", "mix")
    languages = list(dict.fromkeys(([request.language] if chosen else []) + taste.languages))
    return taste.model_copy(update={"genres": genres[:10], "languages": languages[:5]})


class CurateService:
    def __init__(
        self,
        spotify: TrackSearcher,
        analyzer: MoodAnalyzer,
        kb: GenreKnowledge,
        lastfm: LastFm | None = None,
        variety: float = 0.0,
        rng: random.Random | None = None,
        deezer: TempoSource | None = None,
    ) -> None:
        self._spotify = spotify
        self._analyzer = analyzer
        self._kb = kb
        self._lastfm = lastfm
        self._variety = variety
        self._rng = rng or random.Random()  # noqa: S311 - variety, not security
        self._deezer = deezer

    async def _score(
        self, candidates: list[Candidate], mood: MoodProfile, taste: Taste, recently: set[str]
    ) -> tuple[list[ScoredTrack], dict[str, TrackProfile]]:
        """Profiles (Last.fm or fallback), scores, freshness and variety for candidates."""
        if self._lastfm:
            ordered = sorted(candidates, key=_tagging_order)
            hints = {c.track.id: _hints(c, self._kb) for c in ordered}
            profiles = await profile_tracks(
                self._lastfm, [c.track for c in ordered], self._kb, hints=hints
            )
        else:
            profiles = {c.track.id: _fallback_profile(c, self._kb) for c in candidates}
        moods = {i: p.mood for i, p in profiles.items() if p.mood is not None}

        scored = score_candidates(candidates, mood, taste, self._kb, self._analyzer, moods)
        for item in scored:
            if item.candidate.track.id in recently:
                item.score -= RECENT_PENALTY
            if self._variety:
                item.score += self._rng.uniform(0, self._variety)
            # A song you know but whose feel (per listeners) is wrong for now: less likely
            if item.known and item.mood_source == "lastfm" and item.mood_fit < OFF_VIBE:
                item.score -= OFF_VIBE_PENALTY
            item.score = round(max(0.0, min(1.0, item.score)), 3)
            profile = profiles.get(item.candidate.track.id) or _fallback_profile(
                item.candidate, self._kb
            )
            item.genre, item.language = profile.genre, profile.language
        _share_by_artist(scored)
        return scored, profiles

    async def preview(
        self, request: CurateRequest, personal: Personal | None = None
    ) -> CuratePreview:
        taste = request.taste or Taste()
        bad_genres = [g for g in taste.genres if g not in self._kb.genres]
        bad_languages = [code for code in taste.languages if code not in self._kb.languages]
        if request.genre and request.genre not in self._kb.genres:
            bad_genres.append(request.genre)
        if request.language not in ("auto", "mix", *self._kb.languages):
            bad_languages.append(request.language)
        if bad_genres or bad_languages:
            raise UnknownTasteError(bad_genres, bad_languages)

        mood = self._analyzer.analyze(request.mood)  # raises UnknownChipError
        music = personal.music if personal else None
        recent = personal.recent if personal else None

        similar_task = (
            find_similar(self._lastfm, taste) if self._lastfm and taste.artists else _no_similar()
        )
        familiar_task = familiar_candidates(music) if music else _no_candidates()
        recent_task = recent.get(personal.user_id) if recent and personal else _no_ids()
        similar, familiar, recent_ids = await asyncio.gather(
            similar_task, familiar_task, recent_task
        )

        taste = _planning_taste(taste, request)
        plans = plan_searches(mood, taste, self._kb, similar)
        searched = await gather_candidates(self._spotify, plans)
        excluded = set(request.exclude_track_ids)
        candidates = [
            c for c in keep_allowed(_merge(searched, familiar), taste) if c.track.id not in excluded
        ]

        recently = set(recent_ids)
        scored, profiles = await self._score(candidates, mood, taste, recently)

        # One language per playlist: if too few songs are known to be in it, search more
        target = choose_language(scored, request.size, request.language, taste.languages)
        in_language = sum(1 for s in scored if s.language == target)
        if target and in_language < request.size * ROOM:
            searched_genres = {p.value for p in plans if p.kind == "genre"}
            more_plans = language_searches(mood, target, self._kb, searched_genres)
            seen = {c.track.id for c in candidates} | excluded
            more = [
                c
                for c in keep_allowed(await gather_candidates(self._spotify, more_plans), taste)
                if c.track.id not in seen
            ]
            if more:
                plans += more_plans
                candidates += more
                more_scored, more_profiles = await self._score(more, mood, taste, recently)
                scored += more_scored
                profiles |= more_profiles
                _share_by_artist(scored)

        moods = {i: p.mood for i, p in profiles.items() if p.mood is not None}
        scored, focus = focus_playlist(
            scored, request.size, self._kb, target or "mix", request.genre, taste.languages
        )
        if self._deezer:
            await add_tempo(self._deezer, scored, mood.tempo, request.size)

        familiarity = (
            request.familiarity if request.familiarity is not None else MODE_FAMILIARITY[mood.mode]
        )
        picked = pick_mixed(scored, request.size, familiarity)
        coverage = Coverage(
            candidates=len(candidates),
            with_mood=len(moods),
            with_language=sum(1 for p in profiles.values() if p.language),
            with_genre=sum(1 for p in profiles.values() if p.genre),
            with_tempo=sum(1 for s in scored if s.bpm),
        )
        logger.info("Curated", extra={"coverage": coverage.model_dump(), "focus": focus.__dict__})
        if recent and personal and picked:
            try:
                await recent.remember(personal.user_id, [p.candidate.track.id for p in picked])
            except Exception:  # remembering is a nicety; never fail the playlist for it
                logger.warning("Could not remember recent picks", exc_info=True)

        tracks = [
            CuratedTrack(
                track=item.candidate.track,
                score=item.score,
                mood_fit=item.mood_fit,
                taste_fit=item.taste_fit,
                reason=explain(item, mood, taste, self._kb),
                known=item.known,
                tags=item.tag_words,
                bpm=item.bpm,
                tempo=item.tempo,  # type: ignore[arg-type]
                genre=self._kb.genres[item.genre].name if item.genre in self._kb.genres else None,
                language=item.language,
            )
            for item in picked
        ]
        note = None
        if len(tracks) < request.size and focus.language:
            name = self._kb.languages.get(focus.language, focus.language)
            note = (
                f"Found {len(tracks)} {name} songs that fit. Muse only uses songs it knows are "
                f"in {name}; add {name} artists to your Music DNA for longer playlists."
            )
        elif len(tracks) < request.size:
            note = (
                f"Found {len(tracks)} of {request.size} tracks. "
                "Try adding artists or genres, or allowing explicit songs."
            )
        return CuratePreview(
            mood=mood,
            tracks=tracks,
            searches=len(plans),
            candidates_considered=len(candidates),
            note=note,
            familiarity=familiarity,
            personal=bool(familiar),
            mood_data="lastfm" if moods else "estimated",
            similar_artists=list(similar),
            language=focus.language,
            genre=focus.genre,
            coverage=coverage,
        )


async def _no_similar() -> dict[str, str]:
    return {}


async def _no_candidates() -> list[Candidate]:
    return []


async def _no_ids() -> list[str]:
    return []


async def open_deezer(request: Request) -> AsyncIterator[DeezerClient | None]:
    """FastAPI dependency: a Deezer client for song tempo (no key needed; can be switched off)."""
    if not request.app.state.settings.deezer_enabled:
        yield None
        return
    async with httpx2.AsyncClient(timeout=3.0) as http:
        yield DeezerClient(http)


async def open_lastfm(request: Request) -> AsyncIterator[LastFmClient | None]:
    """FastAPI dependency: a Last.fm client, or None when no API key is set."""
    settings = request.app.state.settings
    if not settings.lastfm_configured:
        yield None
        return
    async with httpx2.AsyncClient(timeout=3.0) as http:
        yield LastFmClient(http, settings.lastfm_api_key.get_secret_value())


def get_curate_service(
    spotify: Annotated[SpotifyClient, Depends(open_spotify)],
    analyzer: Annotated[MoodAnalyzer, Depends(get_mood_analyzer)],
    lastfm: Annotated[LastFmClient | None, Depends(open_lastfm)],
    deezer: Annotated[DeezerClient | None, Depends(open_deezer)],
) -> CurateService:
    """FastAPI dependency: a curate service for this request."""
    return CurateService(
        spotify, analyzer, get_genre_knowledge(), lastfm, variety=VARIETY, deezer=deezer
    )

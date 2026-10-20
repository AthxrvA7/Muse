"""Curation: mood + taste -> a ranked, explained playlist preview.

    mood input --MoodAnalyzer--> MoodProfile
    MoodProfile + taste --plan_searches--> Spotify searches
    searches --gather_candidates--> unique candidate tracks
    candidates --keep_allowed + score_candidates--> mood_fit, taste_fit, score
    scores --pick_diverse--> varied top N
    each pick --explain--> one-sentence reason

Nothing here is stored: this is a stateless preview (saving comes in a later slice).
"""

from typing import Annotated

from fastapi import Depends

from app.clients.spotify import SpotifyClient
from app.schemas.curate import (
    CuratedTrack,
    CuratePreview,
    CurateRequest,
    GenreOption,
    TasteOptions,
)
from app.services.mood import get_mood_analyzer
from app.services.mood.analyzer import MoodAnalyzer
from app.services.recommender.candidates import TrackSearcher, gather_candidates
from app.services.recommender.explain import explain
from app.services.recommender.knowledge import GenreKnowledge, get_genre_knowledge
from app.services.recommender.planner import plan_searches
from app.services.recommender.ranking import pick_diverse
from app.services.recommender.scoring import keep_allowed, score_candidates
from app.services.spotify_session import open_spotify


class UnknownTasteError(ValueError):
    def __init__(self, genres: list[str], languages: list[str]) -> None:
        parts = []
        if genres:
            parts.append(f"unknown genre(s): {', '.join(genres)}")
        if languages:
            parts.append(f"unknown language(s): {', '.join(languages)}")
        super().__init__("; ".join(parts).capitalize())


def taste_options(kb: GenreKnowledge) -> TasteOptions:
    return TasteOptions(
        genres=[
            GenreOption(id=gid, name=g.name, languages=g.langs) for gid, g in kb.genres.items()
        ],
        languages=kb.languages,
    )


class CurateService:
    def __init__(self, spotify: TrackSearcher, analyzer: MoodAnalyzer, kb: GenreKnowledge) -> None:
        self._spotify = spotify
        self._analyzer = analyzer
        self._kb = kb

    async def preview(self, request: CurateRequest) -> CuratePreview:
        taste = request.taste
        bad_genres = [g for g in taste.genres if g not in self._kb.genres]
        bad_languages = [code for code in taste.languages if code not in self._kb.languages]
        if bad_genres or bad_languages:
            raise UnknownTasteError(bad_genres, bad_languages)

        mood = self._analyzer.analyze(request.mood)  # raises UnknownChipError
        plans = plan_searches(mood, taste, self._kb)
        candidates = keep_allowed(await gather_candidates(self._spotify, plans), taste)
        scored = score_candidates(candidates, mood, taste, self._kb, self._analyzer)
        picked = pick_diverse(scored, request.size)

        tracks = [
            CuratedTrack(
                track=item.candidate.track,
                score=item.score,
                mood_fit=item.mood_fit,
                taste_fit=item.taste_fit,
                reason=explain(item, mood, taste, self._kb),
            )
            for item in picked
        ]
        note = None
        if len(tracks) < request.size:
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
        )


def get_curate_service(
    spotify: Annotated[SpotifyClient, Depends(open_spotify)],
    analyzer: Annotated[MoodAnalyzer, Depends(get_mood_analyzer)],
) -> CurateService:
    """FastAPI dependency: a curate service for this request."""
    return CurateService(spotify, analyzer, get_genre_knowledge())

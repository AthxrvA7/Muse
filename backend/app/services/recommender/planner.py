"""Query planning: decide which Spotify searches to run for a mood + taste.

Spotify can't search "by mood", so Muse turns the mood into genres that sit
close to it on the valence-energy plane, and combines them with what the user
likes. Each search is tagged with WHY it was chosen; scoring and explanations
use that tag later.
"""

import math
from dataclasses import dataclass
from typing import Literal

from app.clients.spotify import build_query
from app.schemas.curate import Taste
from app.schemas.mood import MoodProfile
from app.services.mood.vocabulary import MoodPoint
from app.services.recommender.knowledge import GenreKnowledge

MAX_ARTIST_SEARCHES = 5
MAX_FAVOURITE_GENRES = 3
MAX_LANGUAGE_GENRES = 2
DISCOVERY_GENRES = 2
MOOD_ONLY_GENRES = 4  # when the user gave no taste at all
MAX_SIMILAR_SEARCHES = 6

Reason = Literal[
    "familiar",  # the user plays it a lot (their Spotify top tracks)
    "favourite_artist",
    "similar_artist",  # by an artist similar to a favourite (Last.fm)
    "favourite_genre",
    "language",
    "discovery",
    "mood",
]


@dataclass(frozen=True)
class SearchPlan:
    """One Spotify search and why Muse is running it."""

    kind: Literal["artist", "genre", "top"]
    value: str  # artist name, genre id, or time range of the user's top tracks
    reason: Reason
    query: str
    fallback_query: str | None = None  # plain keywords if the genre: filter finds too little
    related_to: str | None = None  # for similar artists: the favourite they resemble


def distance(a: MoodPoint, b: MoodPoint) -> float:
    """Straight-line distance on the valence-energy plane (0 = same, ~1.41 = opposite corners)."""
    return math.dist((a.valence, a.energy), (b.valence, b.energy))


def plan_searches(
    mood: MoodProfile,
    taste: Taste,
    kb: GenreKnowledge,
    similar: dict[str, str] | None = None,
) -> list[SearchPlan]:
    """`similar` maps an artist similar to a favourite -> that favourite (from Last.fm)."""
    target = MoodPoint(valence=mood.valence, energy=mood.energy)

    def closest(genre_ids: list[str], count: int) -> list[str]:
        known = [g for g in genre_ids if g in kb.genres]
        return sorted(known, key=lambda g: (distance(kb.genres[g], target), g))[:count]

    def genre_search(genre_id: str, reason: Reason) -> SearchPlan:
        genre = kb.genres[genre_id]
        return SearchPlan(
            kind="genre",
            value=genre_id,
            reason=reason,
            query=build_query(genre=genre.spotify_genre),
            fallback_query=build_query(genre.keywords),
        )

    plans = [
        SearchPlan("artist", name, "favourite_artist", build_query(artist=name))
        for name in taste.artists[:MAX_ARTIST_SEARCHES]
    ]
    plans += [
        SearchPlan("artist", name, "similar_artist", build_query(artist=name), related_to=favourite)
        for name, favourite in list((similar or {}).items())[:MAX_SIMILAR_SEARCHES]
    ]
    chosen: list[str] = []

    for genre_id in closest(taste.genres, MAX_FAVOURITE_GENRES):
        plans.append(genre_search(genre_id, "favourite_genre"))
        chosen.append(genre_id)

    language_genres = [g for g in kb.genres_for_languages(taste.languages) if g not in chosen]
    for genre_id in closest(language_genres, MAX_LANGUAGE_GENRES):
        plans.append(genre_search(genre_id, "language"))
        chosen.append(genre_id)

    # Genres the user can understand: their languages, plus language-neutral ones
    allowed = [
        g
        for g, genre in kb.genres.items()
        if g not in chosen
        and (not taste.languages or not genre.langs or set(genre.langs) & set(taste.languages))
    ]
    if not plans:  # no taste at all: let the mood choose
        plans += [genre_search(g, "mood") for g in closest(allowed, MOOD_ONLY_GENRES)]
    elif mood.mode == "discovery":
        plans += [genre_search(g, "discovery") for g in closest(allowed, DISCOVERY_GENRES)]

    return plans

"""Scoring: how well each candidate fits the mood (mood_fit) and the user's taste (taste_fit).

Mood fit
    Spotify no longer says how a track feels, so Muse estimates it:
    1. from the genre search(es) that found it -> that genre's point in genre_kb.json
    2. else from mood words in the title ("Sad", "Happy", ...) -> that chip's point
    3. else unknown -> neutral 0.5 ("no evidence either way")
    similarity = 1 - distance / sqrt(2): 1 = same spot on the plane, 0 = opposite corners.
    The less certain the estimate, the more it is pulled towards neutral 0.5.

Taste fit
    The strongest reason the track was found: a favourite artist (1.0) beats a
    favourite genre (0.75), which beats a genre in the user's language (0.5).

Score = mood_weight x mood_fit + taste_weight x taste_fit, weights set by the mode.
"""

import math
from dataclasses import dataclass, field

from app.schemas.curate import Taste
from app.schemas.mood import Mode, MoodProfile
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.vocabulary import MoodPoint
from app.services.recommender.candidates import Candidate
from app.services.recommender.knowledge import GenreKnowledge
from app.services.recommender.planner import Reason, distance

MAX_DISTANCE = math.sqrt(2)  # opposite corners of the unit square
NEUTRAL_FIT = 0.5
GENRE_CERTAINTY = 1.0
TITLE_CERTAINTY = 0.8

# (mood weight, taste weight) per playlist mode
MODE_WEIGHTS: dict[Mode, tuple[float, float]] = {
    "comfort": (0.45, 0.55),  # stay close to what the user knows and likes
    "focus": (0.55, 0.45),
    "energy": (0.60, 0.40),
    "discovery": (0.65, 0.35),  # let the mood lead, favourites matter less
}
TASTE_POINTS: dict[Reason, float] = {
    "favourite_artist": 1.0,
    "favourite_genre": 0.75,
    "language": 0.5,
    "discovery": 0.25,
    "mood": 0.25,
}


@dataclass
class ScoredTrack:
    candidate: Candidate
    mood_fit: float
    taste_fit: float
    score: float
    mood_source: str | None  # genre id or mood chip that set the track's estimated feel
    favourite_artist: str | None  # the user's favourite artist on this track, if any
    taste_reason: Reason | None
    mood_genres: list[str] = field(default_factory=list)  # genres averaged into the estimate


def similarity(a: MoodPoint, b: MoodPoint) -> float:
    return max(0.0, 1.0 - distance(a, b) / MAX_DISTANCE)


def estimate_mood(
    candidate: Candidate, kb: GenreKnowledge, analyzer: MoodAnalyzer
) -> tuple[MoodPoint | None, float, list[str]]:
    """Best guess of how a track feels: (point, certainty 0-1, genres or mood word used)."""
    genres = [p.value for p in candidate.sources if p.kind == "genre" and p.value in kb.genres]
    if genres:
        points = [kb.genres[g] for g in genres]
        point = MoodPoint(
            valence=sum(p.valence for p in points) / len(points),
            energy=sum(p.energy for p in points) / len(points),
        )
        return point, GENRE_CERTAINTY, genres

    words = analyzer.mood_words(candidate.track.name)
    if words:
        chip = analyzer.vocabulary.chips[words[0]]
        return MoodPoint(valence=chip.valence, energy=chip.energy), TITLE_CERTAINTY, words[:1]

    return None, 0.0, []


def keep_allowed(candidates: list[Candidate], taste: Taste) -> list[Candidate]:
    """Drop excluded artists and, if asked, explicit tracks."""
    excluded = {name.lower() for name in taste.exclude_artists}
    return [
        c
        for c in candidates
        if (taste.allow_explicit or not c.track.explicit)
        and not any(a.name.lower() in excluded for a in c.track.artists)
    ]


def score_candidates(
    candidates: list[Candidate],
    mood: MoodProfile,
    taste: Taste,
    kb: GenreKnowledge,
    analyzer: MoodAnalyzer,
) -> list[ScoredTrack]:
    target = MoodPoint(valence=mood.valence, energy=mood.energy)
    mood_weight, taste_weight = MODE_WEIGHTS[mood.mode]
    favourites = {name.lower(): name for name in taste.artists}

    scored = []
    for candidate in candidates:
        point, certainty, basis = estimate_mood(candidate, kb, analyzer)
        fit = similarity(point, target) if point else NEUTRAL_FIT
        mood_fit = certainty * fit + (1 - certainty) * NEUTRAL_FIT

        favourite = next(
            (
                favourites[a.name.lower()]
                for a in candidate.track.artists
                if a.name.lower() in favourites
            ),
            None,
        )
        reasons: list[Reason] = [p.reason for p in candidate.sources]
        if favourite:
            reasons.append("favourite_artist")
        taste_fit = max((TASTE_POINTS[r] for r in reasons), default=0.0)
        best = next((r for r in reasons if TASTE_POINTS[r] == taste_fit), None)

        scored.append(
            ScoredTrack(
                candidate=candidate,
                mood_fit=round(mood_fit, 3),
                taste_fit=taste_fit,
                score=round(mood_weight * mood_fit + taste_weight * taste_fit, 3),
                mood_source=basis[0] if basis else None,
                favourite_artist=favourite,
                taste_reason=best,
                mood_genres=[g for g in basis if g in kb.genres],
            )
        )
    return scored

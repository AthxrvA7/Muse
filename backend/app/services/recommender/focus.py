"""Keeping a playlist coherent: one language, one genre (with close neighbours), right tempo.

1. Language: "auto" picks the language with the most weight among the best candidates
   (so it follows the user's own songs and taste); a code forces it; "mix" turns this off.
   The playlist then holds ONLY songs known to be in that language (plus instrumental
   genres, where language doesn't matter). Songs of unknown language are never used:
   a shorter playlist is better than a mixed one. (Curate searches for more songs in
   the language first when there are too few.)
2. Genre: the anchor is the genre with the most weight among the best candidates (or
   the one the user asked for). Each song gets a coherence 0-1 from genre_kb.json
   (same genre, same family, related family, unrelated) that nudges its score, and
   unrelated genres are left out while there are enough other songs.
3. Tempo: the BPM of the best candidates (Deezer) nudges songs whose pace fits the mood.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from app.schemas.catalog import Track
from app.schemas.mood import Tempo
from app.services.recommender.knowledge import GenreKnowledge
from app.services.recommender.scoring import ScoredTrack

VOTERS_PER_SLOT = 3  # the top (3 x playlist size) candidates vote for language and genre
UNKNOWN_GENRE_PENALTY = 0.05
PREFERRED_LANGUAGE_BOOST = 1.5  # languages in the user's taste count more in the auto vote
COHERENCE_WEIGHT = 0.3  # score += 0.3 x (coherence - 0.5): -0.15 .. +0.15
CHOSEN_GENRE_WEIGHT = 0.6  # stronger when the user picked the genre themselves
ROOM = 1.5  # leave unrelated genres out while 1.5x the playlist size remains
TEMPO_WEIGHT = 0.05
TEMPO_BUDGET_SECONDS = 4.0
SLOW_BELOW, FAST_ABOVE = 95.0, 125.0


@dataclass(frozen=True)
class Focus:
    language: str | None
    genre: str | None


def _vote(
    items: list[ScoredTrack], key: str, size: int, boost: frozenset[str] = frozenset()
) -> str | None:
    weights: dict[str, float] = defaultdict(float)
    for item in sorted(items, key=lambda s: -s.score)[: size * VOTERS_PER_SLOT]:
        value = getattr(item, key)
        if value:
            weights[value] += item.score * (PREFERRED_LANGUAGE_BOOST if value in boost else 1.0)
    return max(weights, key=lambda v: (weights[v], v)) if weights else None


def _language_neutral(item: ScoredTrack, kb: GenreKnowledge) -> bool:
    genre = kb.genres.get(item.genre or "")
    return genre is not None and (not genre.langs or genre.family == "chill & instrumental")


def choose_language(
    scored: list[ScoredTrack], size: int, language: str = "auto", preferred: list[str] | None = None
) -> str | None:
    """The playlist's language: the one asked for, none for "mix", or for "auto" the
    user's only taste language (if there are songs in it) or the best candidates' vote."""
    if language == "mix":
        return None
    if language != "auto":
        return language
    preferred = preferred or []
    if len(preferred) == 1 and sum(s.language == preferred[0] for s in scored) >= size // 2:
        return preferred[0]
    return _vote(scored, "language", size, frozenset(preferred))


def focus_playlist(
    scored: list[ScoredTrack],
    size: int,
    kb: GenreKnowledge,
    language: str = "auto",
    genre: str | None = None,
    preferred: list[str] | None = None,
) -> tuple[list[ScoredTrack], Focus]:
    """Scores adjusted and off-language / off-genre songs removed (while enough remain).

    `preferred` are the languages in the user's taste: with exactly one, "auto" uses it
    (if there are songs in it); with several, they count more in the vote.
    """
    target = choose_language(scored, size, language, preferred)

    pool = scored
    if target:  # only songs known to be in the language, plus instrumental ones
        pool = [
            s
            for s in scored
            if s.language == target or (s.language is None and _language_neutral(s, kb))
        ]

    # The anchor comes from songs in the playlist's language when there are any
    voters = [s for s in pool if s.language == target] if target else pool
    chosen = genre if genre in kb.genres else None
    anchor = chosen or _vote(voters, "genre", size) or _vote(pool, "genre", size)
    if anchor:
        weight = CHOSEN_GENRE_WEIGHT if chosen else COHERENCE_WEIGHT
        fits = {id(item): kb.coherence(item.genre, anchor) for item in pool}
        for item in pool:
            item.score += weight * (fits[id(item)] - 0.5)
        # Same or related genres; songs the user knows count as close when their genre is
        # unknown (their own taste is never "off-genre" just because Muse can't tell)
        close = [s for s in pool if (s.genre and fits[id(s)] > 0) or (s.known and not s.genre)]
        unknown_genre = [s for s in pool if not s.genre and not s.known]
        unrelated = [s for s in pool if s.genre and fits[id(s)] == 0]
        pool = close
        if len(pool) < size * ROOM:
            for item in unknown_genre:
                item.score -= UNKNOWN_GENRE_PENALTY
            pool += unknown_genre
        if len(pool) < size:
            pool += unrelated

    for item in pool:
        item.score = round(max(0.0, min(1.0, item.score)), 3)
    return pool, Focus(language=target, genre=anchor)


class TempoSource(Protocol):
    async def bpm(self, isrc: str | None, artist: str, title: str) -> float | None: ...


def tempo_of(bpm: float) -> Tempo:
    if bpm < SLOW_BELOW:
        return "slow"
    return "fast" if bpm > FAST_ABOVE else "medium"


async def add_tempo(
    source: TempoSource,
    scored: list[ScoredTrack],
    target: Tempo,
    size: int,
    budget: float = TEMPO_BUDGET_SECONDS,
) -> None:
    """Looks up the BPM of the best 2 x size candidates and nudges those whose pace fits."""
    best = sorted(scored, key=lambda s: -s.score)[: size * 2]

    async def one(item: ScoredTrack) -> tuple[ScoredTrack, float | None]:
        track: Track = item.candidate.track
        artist = track.artists[0].name if track.artists else ""
        return item, await source.bpm(track.isrc, artist, track.name)

    tasks = [asyncio.ensure_future(one(item)) for item in best]
    if not tasks:
        return
    done, pending = await asyncio.wait(tasks, timeout=budget)
    for task in pending:
        task.cancel()
    order = ["slow", "medium", "fast"]
    for task in done:
        if task.cancelled() or task.exception() is not None:
            continue
        item, bpm = task.result()
        if not bpm:
            continue
        item.bpm, item.tempo = bpm, tempo_of(bpm)
        gap = abs(order.index(item.tempo) - order.index(target))
        item.score = round(max(0.0, min(1.0, item.score + TEMPO_WEIGHT * (1 - gap))), 3)

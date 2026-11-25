"""Keeping a playlist coherent: one language, one genre (with close neighbours), right tempo.

1. Language: "auto" picks the language with the most weight among the best candidates
   (so it follows the user's own songs and taste); a code forces it; "mix" turns this off.
   Songs in another language are left out; songs of unknown language stay, slightly
   lower, unless their genre is instrumental (language doesn't matter there).
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
UNKNOWN_LANGUAGE_PENALTY = 0.08
OTHER_LANGUAGE_PENALTY = 0.3  # only used if there aren't enough songs in the language
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


def _vote(items: list[ScoredTrack], key: str, size: int) -> str | None:
    weights: dict[str, float] = defaultdict(float)
    for item in sorted(items, key=lambda s: -s.score)[: size * VOTERS_PER_SLOT]:
        value = getattr(item, key)
        if value:
            weights[value] += item.score
    return max(weights, key=lambda v: (weights[v], v)) if weights else None


def _language_neutral(item: ScoredTrack, kb: GenreKnowledge) -> bool:
    genre = kb.genres.get(item.genre or "")
    return genre is not None and (not genre.langs or genre.family == "chill & instrumental")


def focus_playlist(
    scored: list[ScoredTrack],
    size: int,
    kb: GenreKnowledge,
    language: str = "auto",
    genre: str | None = None,
) -> tuple[list[ScoredTrack], Focus]:
    """Scores adjusted and off-language / off-genre songs removed (while enough remain)."""
    target = None if language == "mix" else (language if language != "auto" else None)
    if language == "auto":
        target = _vote(scored, "language", size)

    pool = scored
    if target:
        same = [s for s in scored if s.language == target]
        unknown = [s for s in scored if s.language is None]
        for item in unknown:
            if not _language_neutral(item, kb):
                item.score -= UNKNOWN_LANGUAGE_PENALTY
        pool = same + unknown
        if len(pool) < size:  # not enough in that language: let others fill, lower down
            others = [s for s in scored if s.language not in (target, None)]
            for item in others:
                item.score -= OTHER_LANGUAGE_PENALTY
            pool += others

    # The anchor comes from songs in the playlist's language when there are any
    voters = [s for s in pool if s.language == target] if target else pool
    chosen = genre if genre in kb.genres else None
    anchor = chosen or _vote(voters, "genre", size) or _vote(pool, "genre", size)
    if anchor:
        weight = CHOSEN_GENRE_WEIGHT if chosen else COHERENCE_WEIGHT
        fits = {id(item): kb.coherence(item.genre, anchor) for item in pool}
        for item in pool:
            item.score += weight * (fits[id(item)] - 0.5)
        related = [s for s in pool if fits[id(s)] > 0]
        if len(related) >= size * ROOM:
            pool = related

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

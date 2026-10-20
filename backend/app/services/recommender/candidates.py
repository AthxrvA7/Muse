"""Candidate search: run the planned Spotify searches and collect unique tracks.

Searches run in parallel (at most 4 at a time, to stay polite to Spotify).
One failed search doesn't sink the playlist; only if every search fails is
Spotify reported as unavailable. A rate limit stops everything at once.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Protocol

from app.clients.spotify import SpotifyError, SpotifyRateLimitError, SpotifyUnavailableError
from app.schemas.catalog import Track
from app.services.recommender.planner import SearchPlan

TRACKS_PER_SEARCH = 20
MIN_RESULTS_BEFORE_FALLBACK = 5
MAX_PARALLEL_SEARCHES = 4

logger = logging.getLogger(__name__)


class TrackSearcher(Protocol):
    async def search_tracks(self, query: str, total: int = ...) -> list[Track]: ...


UNRANKED = 10**6


@dataclass
class Candidate:
    track: Track
    sources: list[SearchPlan] = field(default_factory=list)  # every search that found it
    # Best position in any Spotify result list (0 = top hit). Spotify orders results by
    # relevance, so this breaks ties between tracks Muse scores the same.
    best_rank: int = UNRANKED


async def _run(spotify: TrackSearcher, plan: SearchPlan, limit: asyncio.Semaphore) -> list[Track]:
    async with limit:
        tracks = await spotify.search_tracks(plan.query, total=TRACKS_PER_SEARCH)
        if plan.fallback_query and len(tracks) < MIN_RESULTS_BEFORE_FALLBACK:
            seen = {t.id for t in tracks}
            extra = await spotify.search_tracks(plan.fallback_query, total=TRACKS_PER_SEARCH)
            tracks += [t for t in extra if t.id not in seen]
        return tracks


async def gather_candidates(spotify: TrackSearcher, plans: list[SearchPlan]) -> list[Candidate]:
    limit = asyncio.Semaphore(MAX_PARALLEL_SEARCHES)
    results = await asyncio.gather(
        *(_run(spotify, p, limit) for p in plans), return_exceptions=True
    )

    candidates: dict[str, Candidate] = {}
    failures = 0
    for plan, result in zip(plans, results, strict=True):
        if isinstance(result, SpotifyRateLimitError):
            raise result
        if isinstance(result, SpotifyError):
            failures += 1
            logger.warning("A candidate search failed", extra={"search_kind": plan.kind})
            continue
        if isinstance(result, BaseException):
            raise result
        for rank, track in enumerate(result):
            candidate = candidates.setdefault(track.id, Candidate(track))
            candidate.best_rank = min(candidate.best_rank, rank)
            if plan not in candidate.sources:  # a search may return the same track twice
                candidate.sources.append(plan)

    if plans and failures == len(plans):
        raise SpotifyUnavailableError("Every candidate search failed")
    return list(candidates.values())

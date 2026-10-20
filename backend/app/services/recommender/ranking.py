"""Diversity re-ranking: turn a scored list into a varied playlist.

Highest score first, but:
- at most 2 songs per artist, counting every credited artist (Bollywood songs
  often list the singer third or fourth), so one artist can't fill the playlist
- at most 40% from any one search, so one genre (or artist search) can't either
- versions of the same song ("Song", "Song - Remastered", "Song (Live)") count once
If there aren't enough candidates, the limits are relaxed to fill the playlist.
"""

import math
import re

from app.schemas.catalog import Track
from app.services.recommender.scoring import ScoredTrack

MAX_PER_ARTIST = 2
RELAXED_MAX_PER_ARTIST = 4
MAX_SHARE_PER_SEARCH = 0.4


def song_key(track: Track) -> str:
    """Same song + same main artist -> same key, whatever the version label."""
    name = track.name.lower()
    name = re.sub(r"\s[-–]\s.*$", "", name)  # "Song - Remastered 2011"
    name = re.sub(r"[(\[].*?[)\]]", "", name)  # "Song (feat. X)", "Song [Live]"
    artist = track.artists[0].name.lower() if track.artists else ""
    return f"{' '.join(name.split())}|{artist}"


def _artist_ids(item: ScoredTrack) -> list[str]:
    return [artist.id for artist in item.candidate.track.artists]


def _main_search(item: ScoredTrack) -> str:
    """The search that gave the track its taste reason (else the first that found it)."""
    sources = item.candidate.sources
    plan = next((p for p in sources if p.reason == item.taste_reason), None) or (
        sources[0] if sources else None
    )
    # No recorded search: the track is its own group, so it never shares a cap
    return f"{plan.kind}:{plan.value}" if plan else f"track:{item.candidate.track.id}"


def pick_diverse(scored: list[ScoredTrack], size: int) -> list[ScoredTrack]:
    # Highest score first; equal scores -> Spotify's own order (top hits first)
    ranked = sorted(scored, key=lambda s: (-s.score, s.candidate.best_rank, s.candidate.track.id))
    picked: list[ScoredTrack] = []
    seen_songs: set[str] = set()
    limits = [
        (MAX_PER_ARTIST, math.ceil(size * MAX_SHARE_PER_SEARCH)),  # normal: varied playlist
        (RELAXED_MAX_PER_ARTIST, size),  # few candidates: fill the playlist anyway
    ]

    for artist_cap, search_cap in limits:
        per_artist: dict[str, int] = {}
        per_search: dict[str, int] = {}
        for item in picked:
            for artist in _artist_ids(item):
                per_artist[artist] = per_artist.get(artist, 0) + 1
            per_search[_main_search(item)] = per_search.get(_main_search(item), 0) + 1
        for item in ranked:
            if len(picked) >= size:
                return picked
            key = song_key(item.candidate.track)
            artists = _artist_ids(item)
            search = _main_search(item)
            if (
                key in seen_songs
                or any(per_artist.get(a, 0) >= artist_cap for a in artists)
                or per_search.get(search, 0) >= search_cap
            ):
                continue
            picked.append(item)
            seen_songs.add(key)
            for artist in artists:
                per_artist[artist] = per_artist.get(artist, 0) + 1
            per_search[search] = per_search.get(search, 0) + 1
    return picked

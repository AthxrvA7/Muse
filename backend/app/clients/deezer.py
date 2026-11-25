"""Deezer public API: the tempo (BPM) of a song.

Spotify no longer gives apps a song's tempo; Deezer's free public API does (no key or
login needed). Muse finds the same recording by its ISRC (the standard recording code
Spotify also returns), else by artist and title. Answers are cached for a day; any
failure means "tempo unknown".
"""

import asyncio
import logging
from typing import Any

import httpx2

from app.clients.lastfm import TTLCache

API_URL = "https://api.deezer.com"
MAX_PARALLEL = 6  # Deezer allows about 50 requests per 5 seconds

logger = logging.getLogger(__name__)

_cache = TTLCache()


def _bpm(body: dict[str, Any]) -> float | None:
    try:
        bpm = float(body.get("bpm") or 0)
    except (TypeError, ValueError):
        return None
    return round(bpm, 1) if 40 <= bpm <= 250 else None  # 0 means Deezer doesn't know


class DeezerClient:
    def __init__(self, http: httpx2.AsyncClient, cache: TTLCache | None = None) -> None:
        self._http = http
        self._cache = cache if cache is not None else _cache
        self._limit = asyncio.Semaphore(MAX_PARALLEL)

    async def bpm(self, isrc: str | None, artist: str, title: str) -> float | None:
        key = f"bpm|{isrc or ''}|{artist.lower()}|{title.lower()}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached or None  # 0.0 cached = known to be unknown
        found = None
        if isrc:
            found = _bpm(await self._get(f"/track/isrc:{isrc}"))
        if found is None:
            query = f'artist:"{artist}" track:"{title}"'.replace("\\", "")
            hits = (await self._get("/search", {"q": query, "limit": "1"})).get("data") or []
            if hits and isinstance(hits[0], dict) and hits[0].get("id"):
                found = _bpm(await self._get(f"/track/{int(hits[0]['id'])}"))
        self._cache.put(key, found or 0.0)
        return found

    async def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        async with self._limit:
            try:
                response = await self._http.get(f"{API_URL}{path}", params=params)
                body = response.json() if response.status_code == 200 else {}
            except (httpx2.TransportError, ValueError):
                logger.warning("Deezer did not answer")
                return {}
        if not isinstance(body, dict) or "error" in body:
            return {}
        return body

"""Deezer public API: a song's tempo (BPM) and its 30-second preview.

Spotify no longer gives apps a song's tempo or previews; Deezer's free public API does
(no key or login needed, about 50 requests per 5 seconds). Muse finds the same recording
by its ISRC (the standard recording code Spotify also returns), else by artist and title.

- The match (Deezer track ID + BPM) is cached for a day: it never changes.
- Preview links are signed and expire within minutes, so they are never stored: Muse
  asks Deezer for a fresh one when the user presses play, and keeps it only until
  shortly before its own expiry time (at most 10 minutes).
- Any failure means "unknown": no tempo, or no preview button.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, TypeGuard
from urllib.parse import urlparse

import httpx2

from app.clients.lastfm import TTLCache

API_URL = "https://api.deezer.com"
MAX_PARALLEL = 6  # Deezer allows about 50 requests per 5 seconds
PREVIEW_MAX_SECONDS = 600  # keep a fresh preview link at most 10 minutes...
PREVIEW_MARGIN_SECONDS = 60  # ...and never closer than 1 minute to its expiry
PREVIEW_HOST = ".dzcdn.net"

logger = logging.getLogger(__name__)

_cache = TTLCache()


def _bpm(body: dict[str, Any]) -> float | None:
    try:
        bpm = float(body.get("bpm") or 0)
    except (TypeError, ValueError):
        return None
    return round(bpm, 1) if 40 <= bpm <= 250 else None  # 0 means Deezer doesn't know


@dataclass(frozen=True)
class DeezerMatch:
    deezer_id: int | None
    bpm: float | None


def _match(body: dict[str, Any]) -> DeezerMatch:
    try:
        deezer_id = int(body["id"]) if body.get("id") else None
    except (TypeError, ValueError):
        deezer_id = None
    return DeezerMatch(deezer_id, _bpm(body))


def preview_lifetime(url: str, now: float) -> float:
    """Seconds this signed link may be reused: until 1 minute before its `exp`, max 10 min."""
    found = re.search(r"exp=(\d+)", url)
    if not found:
        return 0.0
    return max(0.0, min(PREVIEW_MAX_SECONDS, int(found.group(1)) - now - PREVIEW_MARGIN_SECONDS))


def is_preview_url(url: object) -> TypeGuard[str]:
    """Only https links on Deezer's own CDN are ever handed to the browser."""
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and (parsed.hostname or "").endswith(PREVIEW_HOST)


class DeezerClient:
    def __init__(self, http: httpx2.AsyncClient, cache: TTLCache | None = None) -> None:
        self._http = http
        self._cache = cache if cache is not None else _cache
        self._limit = asyncio.Semaphore(MAX_PARALLEL)

    async def match(self, isrc: str | None, artist: str, title: str) -> DeezerMatch:
        """The same recording on Deezer (its ID and BPM), by ISRC, else by artist and title."""
        key = f"match|{isrc or ''}|{artist.lower()}|{title.lower()}"
        cached = self._cache.get(key)
        if cached is not None:
            return DeezerMatch(*cached)
        found = DeezerMatch(None, None)
        if isrc:
            found = _match(await self._get(f"/track/isrc:{isrc}"))
        if found.deezer_id is None:
            query = f'artist:"{artist}" track:"{title}"'.replace("\\", "")
            hits = (await self._get("/search", {"q": query, "limit": "1"})).get("data") or []
            if hits and isinstance(hits[0], dict) and hits[0].get("id"):
                found = _match(await self._get(f"/track/{int(hits[0]['id'])}"))
        self._cache.put(key, (found.deezer_id, found.bpm))
        return found

    async def bpm(self, isrc: str | None, artist: str, title: str) -> float | None:
        return (await self.match(isrc, artist, title)).bpm

    async def preview_url(self, deezer_id: int) -> str | None:
        """A fresh, signed 30-second preview link for a Deezer track (or None)."""
        key = f"preview|{deezer_id}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached or None
        url = (await self._get(f"/track/{deezer_id}")).get("preview")
        if not is_preview_url(url):
            self._cache.put(
                key, "", seconds=PREVIEW_MAX_SECONDS
            )  # no preview: don't ask again soon
            return None
        lifetime = preview_lifetime(url, time.time())
        if lifetime > 0:
            self._cache.put(key, url, seconds=lifetime)
        return url

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

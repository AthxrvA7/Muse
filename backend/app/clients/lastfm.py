"""Last.fm client: listener tags (how a song feels) and similar artists.

Spotify no longer tells apps how a song feels, but millions of Last.fm listeners tag
songs with words like "chill", "sad" or "party". Muse reads those tags to place each
song on its mood map, and asks Last.fm for artists similar to the user's favourites.

- The API key travels in the query string, so URLs are never logged (and the log
  filter masks ``api_key=`` anyway).
- Answers are cached in memory for a day: tags rarely change, and a cached curate is fast.
- Every failure becomes "no data": Muse then falls back to its own estimate.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

import httpx2

API_URL = "https://ws.audioscrobbler.com/2.0/"
CACHE_SECONDS = 24 * 3600
CACHE_ENTRIES = 20_000
MAX_PARALLEL = 8

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tag:
    name: str  # lower-case, e.g. "late night"
    count: int  # Last.fm's relative weight, 0-100 (100 = the song's strongest tag)


class TTLCache:
    """A small in-memory cache with expiry; the oldest entries go first when full."""

    def __init__(self, seconds: float = CACHE_SECONDS, size: int = CACHE_ENTRIES) -> None:
        self._seconds = seconds
        self._size = size
        self._items: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None or item[0] < time.monotonic():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return item[1]

    def put(self, key: str, value: Any) -> None:
        self._items[key] = (time.monotonic() + self._seconds, value)
        self._items.move_to_end(key)
        while len(self._items) > self._size:
            self._items.popitem(last=False)


# One cache per process, shared by every request
_cache = TTLCache()


def _as_list(value: Any) -> list[dict[str, Any]]:
    # Last.fm returns a single object instead of a one-item list
    if isinstance(value, dict):
        return [value]
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _tags(body: dict[str, Any]) -> list[Tag]:
    tags = []
    for item in _as_list((body.get("toptags") or {}).get("tag")):
        name = " ".join(str(item.get("name", "")).lower().split())
        try:
            count = int(item.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        if name and count > 0:
            tags.append(Tag(name, count))
    return tags


class LastFmClient:
    def __init__(
        self, http: httpx2.AsyncClient, api_key: str, cache: TTLCache | None = None
    ) -> None:
        self._http = http
        self._key = api_key
        self._cache = cache if cache is not None else _cache
        self._limit = asyncio.Semaphore(MAX_PARALLEL)

    async def track_tags(self, artist: str, track: str) -> list[Tag]:
        body = await self._call("track.gettoptags", artist=artist, track=track)
        return _tags(body)

    async def artist_tags(self, artist: str) -> list[Tag]:
        return _tags(await self._call("artist.gettoptags", artist=artist))

    async def similar_artists(self, artist: str, limit: int = 8) -> list[str]:
        body = await self._call("artist.getsimilar", artist=artist, limit=str(limit))
        items = _as_list((body.get("similarartists") or {}).get("artist"))
        return [str(item["name"]) for item in items if item.get("name")][:limit]

    async def _call(self, method: str, **params: str) -> dict[str, Any]:
        key = method + "|" + "|".join(f"{k}={v.lower()}" for k, v in sorted(params.items()))
        cached = self._cache.get(key)
        if cached is not None:
            return dict(cached)
        query = {"method": method, "autocorrect": "1", "format": "json", **params}
        async with self._limit:
            try:
                response = await self._http.get(API_URL, params={**query, "api_key": self._key})
                body = response.json() if response.status_code in (200, 404) else None
            except (httpx2.TransportError, ValueError):
                logger.warning("Last.fm did not answer", extra={"lastfm_method": method})
                return {}  # not cached: try again next time
        if not isinstance(body, dict):
            logger.warning(
                "Last.fm request failed",
                extra={"lastfm_method": method, "status_code": response.status_code},
            )
            return {}
        if "error" in body:  # e.g. 6 = not found: a real answer, cache it as "nothing"
            body = {}
        self._cache.put(key, body)
        return body

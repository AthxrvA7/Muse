"""The only code in Muse that talks to Spotify.

Search (Feb 2026 rules): at most 10 results per request, so longer result lists
are fetched page by page with `offset` (0, 10, 20, ...). A `market` (country) is
required because client-credentials requests have no user country.

Authentication: client-credentials flow (app-level, no user login). Muse gets an
access token with its Client ID + Secret, caches it until shortly before it
expires (Spotify issues 1-hour tokens), and refreshes it automatically.

Failure handling, for every API call:
- 401 (token expired or revoked) -> get a fresh token and retry once
- 429 (rate limited)             -> wait for Retry-After (max 5 s) and retry once
- 5xx or timeout                 -> retry once, then report Spotify as unavailable
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx2

from app.schemas.catalog import Artist, ArtistRef, Track

TOKEN_URL = "https://accounts.spotify.com/api/token"  # noqa: S105 - a URL, not a password
API_URL = "https://api.spotify.com/v1"
TOKEN_REFRESH_MARGIN = 60  # seconds: refresh a token this long before it expires
MAX_RETRY_AFTER = 5  # seconds: never wait longer than this on a 429
PAGE_SIZE = 10  # Spotify's maximum `limit` per search request
MAX_OFFSET = 1000  # Spotify's maximum `offset`
MAX_TERM_LENGTH = 100

logger = logging.getLogger(__name__)


class SpotifyError(Exception):
    """Base class: something went wrong talking to Spotify."""


class SpotifyAuthError(SpotifyError):
    """Spotify rejected Muse's Client ID / Secret."""


class SpotifyRateLimitError(SpotifyError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Spotify rate limit reached; retry after {retry_after} s")
        self.retry_after = retry_after


class SpotifyUnavailableError(SpotifyError):
    """Spotify timed out or returned a server error twice in a row."""


@dataclass
class AccessToken:
    value: str
    expires_at: float  # time.monotonic() deadline

    def is_fresh(self) -> bool:
        return time.monotonic() < self.expires_at - TOKEN_REFRESH_MARGIN


class TokenCache:
    """Keeps the current app token between requests (one per process)."""

    def __init__(self) -> None:
        self.token: AccessToken | None = None


class SpotifyClient:
    def __init__(
        self,
        http: httpx2.AsyncClient,
        client_id: str,
        client_secret: str,
        market: str,
        cache: TokenCache,
    ) -> None:
        self._http = http
        self._client_id = client_id
        self._client_secret = client_secret
        self.market = market
        self._cache = cache

    # ---------- authentication ----------

    async def _token(self, *, force_refresh: bool = False) -> str:
        cached = self._cache.token
        if cached and cached.is_fresh() and not force_refresh:
            return cached.value

        try:
            response = await self._http.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=httpx2.BasicAuth(self._client_id, self._client_secret),
            )
        except httpx2.TransportError as error:
            raise SpotifyUnavailableError("Could not reach Spotify accounts service") from error

        if response.status_code in (400, 401):
            logger.error(
                "Spotify rejected the client credentials (status %s)", response.status_code
            )
            raise SpotifyAuthError("Spotify rejected Muse's client credentials")
        if response.status_code != 200:
            raise SpotifyUnavailableError(f"Spotify token endpoint returned {response.status_code}")

        body = response.json()
        self._cache.token = AccessToken(
            value=body["access_token"], expires_at=time.monotonic() + int(body["expires_in"])
        )
        return self._cache.token.value

    # ---------- requests ----------

    async def get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET an API path with automatic token refresh and one retry on transient errors."""
        refreshed = waited = retried = False
        while True:
            token = await self._token(force_refresh=refreshed)
            try:
                response = await self._http.get(
                    f"{API_URL}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except httpx2.TransportError as error:  # timeouts and connection errors
                if retried:
                    raise SpotifyUnavailableError("Spotify did not respond") from error
                retried = True
                continue

            status = response.status_code
            if status == 200:
                result: dict[str, Any] = response.json()
                return result
            if status == 401 and not refreshed:
                refreshed = True
                continue
            if status == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                if waited or retry_after > MAX_RETRY_AFTER:
                    raise SpotifyRateLimitError(retry_after)
                waited = True
                await asyncio.sleep(retry_after)
                continue
            if status >= 500 and not retried:
                retried = True
                continue

            logger.warning("Spotify request failed", extra={"path": path, "status_code": status})
            if status >= 500:
                raise SpotifyUnavailableError(f"Spotify returned {status}")
            raise SpotifyError(f"Spotify returned {status} for {path}")

    # ---------- search ----------

    async def search_tracks(self, query: str, total: int = PAGE_SIZE) -> list[Track]:
        items = await self._search(query, "track", total)
        return [track for item in items if (track := _parse_track(item))]

    async def search_artists(self, query: str, total: int = PAGE_SIZE) -> list[Artist]:
        items = await self._search(query, "artist", total)
        return [artist for item in items if (artist := _parse_artist(item))]

    async def _search(
        self, query: str, kind: Literal["track", "artist"], total: int
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        offset = 0
        while len(results) < total and offset <= MAX_OFFSET:
            limit = min(PAGE_SIZE, total - len(results))
            body = await self.get(
                "/search",
                {"q": query, "type": kind, "market": self.market, "limit": limit, "offset": offset},
            )
            page = [item for item in body.get(f"{kind}s", {}).get("items", []) if item]
            results.extend(page)
            if len(page) < limit:  # Spotify has no more results
                break
            offset += limit
        return results


# ---------- building queries ----------


def _clean(term: str) -> str:
    """Make user text safe inside a Spotify query: no quotes, no control characters."""
    term = re.sub(r'["\x00-\x1f]', " ", term)
    return " ".join(term.split())[:MAX_TERM_LENGTH]


def build_query(
    text: str = "", *, artist: str | None = None, genre: str | None = None, year: str | None = None
) -> str:
    """Build a Spotify search query, e.g. build_query(artist="Arijit Singh", genre="sufi")
    -> 'artist:"Arijit Singh" genre:"sufi"'."""
    parts = [_clean(text)] if text.strip() else []
    if artist:
        parts.append(f'artist:"{_clean(artist)}"')
    if genre:
        parts.append(f'genre:"{_clean(genre)}"')
    if year and re.fullmatch(r"\d{4}(-\d{4})?", year):
        parts.append(f"year:{year}")
    return " ".join(p for p in parts if p and not p.endswith(':""'))


# ---------- parsing responses ----------


def _image(item: dict[str, Any]) -> str | None:
    images = item.get("images") or []
    return images[0]["url"] if images and images[0].get("url") else None


def _parse_track(item: dict[str, Any]) -> Track | None:
    """Turn a Spotify track object into a Track; skip anything malformed."""
    try:
        album = item.get("album") or {}
        release = str(album.get("release_date") or "")
        return Track(
            id=item["id"],
            name=item["name"],
            artists=[ArtistRef(id=a["id"], name=a["name"]) for a in item.get("artists") or []],
            album=album.get("name", ""),
            release_year=int(release[:4]) if release[:4].isdigit() else None,
            image_url=_image(album),
            spotify_url=item["external_urls"]["spotify"],
            uri=item["uri"],
            explicit=bool(item.get("explicit")),
            duration_ms=int(item.get("duration_ms") or 0),
        )
    except (KeyError, TypeError, ValueError):
        logger.warning("Skipping malformed track from Spotify search")
        return None


def _parse_artist(item: dict[str, Any]) -> Artist | None:
    try:
        return Artist(
            id=item["id"],
            name=item["name"],
            genres=list(item.get("genres") or []),
            image_url=_image(item),
            spotify_url=item["external_urls"]["spotify"],
        )
    except (KeyError, TypeError, ValueError):
        logger.warning("Skipping malformed artist from Spotify search")
        return None

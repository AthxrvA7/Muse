"""The only code in Muse that talks to Spotify.

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
import time
from dataclasses import dataclass
from typing import Any

import httpx2

TOKEN_URL = "https://accounts.spotify.com/api/token"  # noqa: S105 - a URL, not a password
API_URL = "https://api.spotify.com/v1"
TOKEN_REFRESH_MARGIN = 60  # seconds: refresh a token this long before it expires
MAX_RETRY_AFTER = 5  # seconds: never wait longer than this on a 429

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

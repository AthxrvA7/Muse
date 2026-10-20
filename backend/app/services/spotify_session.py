"""A Spotify connection for one request, shared by every service that needs Spotify.

Opens an HTTP client for the request and closes it afterwards. The app token is
cached for the whole process (Spotify tokens last an hour).
"""

from collections.abc import AsyncIterator

import httpx2
from fastapi import HTTPException, Request, status

from app.clients.spotify import SpotifyClient, TokenCache

# One app token per process, shared by every request
_token_cache = TokenCache()


async def open_spotify(request: Request) -> AsyncIterator[SpotifyClient]:
    """FastAPI dependency: a ready-to-use Spotify client for this request."""
    settings = request.app.state.settings
    if not settings.spotify_configured:
        # Raised before the route runs, so it must already be an HTTP error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Spotify is not configured on this server"},
        )
    async with httpx2.AsyncClient(timeout=settings.spotify_timeout_seconds) as http:
        yield SpotifyClient(
            http,
            settings.spotify_client_id,
            settings.spotify_client_secret.get_secret_value(),
            settings.spotify_market,
            _token_cache,
        )

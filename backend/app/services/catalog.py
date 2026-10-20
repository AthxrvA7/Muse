"""Catalogue search: find tracks and artists on Spotify.

Routes use this service rather than the Spotify client directly, so the HTTP
layer never depends on how Muse talks to Spotify.
"""

from collections.abc import AsyncIterator
from typing import Literal

import httpx2
from fastapi import HTTPException, Request, status

from app.clients.spotify import SpotifyClient, TokenCache, build_query
from app.schemas.catalog import Artist, Track

# One app token per process, shared by every request
_token_cache = TokenCache()


class CatalogService:
    def __init__(self, spotify: SpotifyClient) -> None:
        self._spotify = spotify

    async def search(
        self, query: str, kind: Literal["track", "artist"], limit: int
    ) -> list[Track] | list[Artist]:
        q = build_query(query)
        if kind == "artist":
            return await self._spotify.search_artists(q, total=limit)
        return await self._spotify.search_tracks(q, total=limit)


async def get_catalog_service(request: Request) -> AsyncIterator[CatalogService]:
    """FastAPI dependency: a catalogue service with a Spotify connection for this request."""
    settings = request.app.state.settings
    if not settings.spotify_configured:
        # Raised here (before the route runs), so it must already be an HTTP error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Spotify is not configured on this server"},
        )
    async with httpx2.AsyncClient(timeout=settings.spotify_timeout_seconds) as http:
        yield CatalogService(
            SpotifyClient(
                http,
                settings.spotify_client_id,
                settings.spotify_client_secret.get_secret_value(),
                settings.spotify_market,
                _token_cache,
            )
        )

"""Catalogue search: find tracks and artists on Spotify.

Routes use this service rather than the Spotify client directly, so the HTTP
layer never depends on how Muse talks to Spotify.
"""

from typing import Annotated, Literal

from fastapi import Depends

from app.clients.spotify import SpotifyClient, build_query
from app.schemas.catalog import Artist, Track
from app.services.spotify_session import open_spotify


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


def get_catalog_service(spotify: Annotated[SpotifyClient, Depends(open_spotify)]) -> CatalogService:
    """FastAPI dependency: a catalogue service for this request."""
    return CatalogService(spotify)

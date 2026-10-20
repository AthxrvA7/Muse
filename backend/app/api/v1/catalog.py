"""Catalogue endpoints: search Spotify for tracks and artists."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.errors import spotify_http_error
from app.clients.spotify import SpotifyError
from app.schemas.catalog import Artist, Track
from app.services.catalog import CatalogService, get_catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/search", summary="Search Spotify for tracks or artists")
async def search_catalog(
    q: Annotated[str, Query(min_length=1, max_length=100, examples=["Prateek Kuhad"])],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    kind: Annotated[Literal["track", "artist"], Query(alias="type")] = "track",
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> list[Track] | list[Artist]:
    try:
        return await service.search(q, kind, limit)
    except SpotifyError as error:
        raise spotify_http_error(error) from error

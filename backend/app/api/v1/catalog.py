"""Catalogue endpoints: search Spotify for tracks and artists."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.clients.spotify import SpotifyError, SpotifyRateLimitError
from app.schemas.catalog import Artist, Track
from app.services.catalog import CatalogService, get_catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


def spotify_http_error(error: SpotifyError) -> HTTPException:
    """Translate a Spotify problem into a clear HTTP error (no internal details)."""
    if isinstance(error, SpotifyRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": "Spotify is busy; try again shortly"},
            headers={"Retry-After": str(error.retry_after)},
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"message": "Spotify is unavailable right now; try again later"},
    )


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

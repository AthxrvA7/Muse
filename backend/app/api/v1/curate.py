"""Curation endpoints: the core of Muse."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.errors import spotify_http_error
from app.clients.spotify import SpotifyError
from app.schemas.curate import CuratePreview, CurateRequest, TasteOptions
from app.services.curate import CurateService, UnknownTasteError, get_curate_service, taste_options
from app.services.mood.analyzer import UnknownChipError
from app.services.recommender.knowledge import get_genre_knowledge

router = APIRouter(prefix="/curate", tags=["curate"])


@router.post("", summary="Curate a playlist for a mood and taste (preview)")
async def curate(
    request: CurateRequest,
    service: Annotated[CurateService, Depends(get_curate_service)],
) -> CuratePreview:
    """Returns ranked tracks, each with a reason. Nothing is saved; mood text is never stored."""
    try:
        return await service.preview(request)
    except UnknownChipError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(error), "allowed_chips": error.allowed},
        ) from error
    except UnknownTasteError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(error), "hint": "See GET /api/v1/curate/options"},
        ) from error
    except SpotifyError as error:
        raise spotify_http_error(error) from error


@router.get("/options", summary="Genres and languages you can use in taste")
def options() -> TasteOptions:
    return taste_options(get_genre_knowledge())

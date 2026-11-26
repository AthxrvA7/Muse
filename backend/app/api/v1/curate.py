"""Curation endpoints: the core of Muse."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import PersonalContext, SavedTaste
from app.api.errors import spotify_http_error
from app.clients.spotify import SpotifyError
from app.schemas.curate import CuratePreview, CurateRequest, TasteOptions
from app.services.curate import CurateService, UnknownTasteError, get_curate_service, taste_options
from app.services.mood.analyzer import UnknownChipError
from app.services.recommender.knowledge import get_genre_knowledge

router = APIRouter(prefix="/curate", tags=["curate"])


@router.post("", summary="Curate a playlist for a mood and taste (preview)")
async def curate(
    http_request: Request,
    request: CurateRequest,
    service: Annotated[CurateService, Depends(get_curate_service)],
    saved_taste: SavedTaste,
    personal: PersonalContext,
) -> CuratePreview:
    """Returns ranked tracks, each with a reason. Mood text is never stored.

    Logged in and no `taste` sent? Your saved taste profile is used. Logged in with
    permission to read your top tracks? Songs you already play are mixed in (see
    `familiarity`), and songs Muse picked for you recently are less likely to repeat.
    """
    if personal is None:  # a visitor: counted against everyone's shared budget
        settings = http_request.app.state.settings
        wait = http_request.app.state.visitor_curations.hit(
            "visitors", settings.curate_visitors_per_minute
        )
        if wait is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"message": "Muse is busy with lots of visitors. Try again in a minute."},
                headers={"Retry-After": str(wait)},
            )
    source = "request" if request.taste is not None else "none"
    if request.taste is None and saved_taste is not None:
        request = request.model_copy(update={"taste": saved_taste})
        source = "saved_profile"
    try:
        preview = await service.preview(request, personal)
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
    return preview.model_copy(update={"taste_source": source})


@router.get("/options", summary="Genres and languages you can use in taste")
def options() -> TasteOptions:
    return taste_options(get_genre_knowledge())

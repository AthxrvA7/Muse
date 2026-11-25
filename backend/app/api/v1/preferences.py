"""The logged-in user's taste profile and Music DNA (Classics: "Know your music")."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, PreferencesRepo, get_taste_import_service
from app.api.errors import spotify_http_error
from app.clients.spotify import SpotifyError
from app.schemas.preferences import (
    MusicDNA,
    PreferencesIn,
    PreferencesOut,
    SpotifyTasteSuggestion,
)
from app.services.auth import NotLoggedInError
from app.services.curate import UnknownTasteError
from app.services.preferences import check_known, music_dna, to_document
from app.services.recommender.knowledge import get_genre_knowledge
from app.services.taste_import import MissingScopeError, TasteImportService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", summary="Your saved taste profile")
async def get_preferences(user: CurrentUser, repo: PreferencesRepo) -> PreferencesOut:
    saved = await repo.get(user.id)
    return PreferencesOut(**saved.model_dump(exclude={"user_id"})) if saved else PreferencesOut()


@router.put("", summary="Save your taste profile (replaces the previous one)")
async def save_preferences(
    body: PreferencesIn, user: CurrentUser, repo: PreferencesRepo
) -> PreferencesOut:
    try:
        check_known(body, get_genre_knowledge())
    except UnknownTasteError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(error), "hint": "See GET /api/v1/curate/options"},
        ) from error
    document = to_document(user.id, body)
    await repo.save(document)
    return PreferencesOut(**document.model_dump(exclude={"user_id"}))


@router.get("/dna", summary="Music DNA: a summary of your stated taste")
async def get_music_dna(user: CurrentUser, repo: PreferencesRepo) -> MusicDNA:
    return music_dna(await repo.get(user.id), get_genre_knowledge())


@router.get(
    "/from-spotify",
    summary="Suggest a taste profile from your Spotify top artists (nothing is saved)",
)
async def suggest_from_spotify(
    user: CurrentUser, service: Annotated[TasteImportService, Depends(get_taste_import_service)]
) -> SpotifyTasteSuggestion:
    try:
        return await service.suggest(user)
    except MissingScopeError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Log in with Spotify again so Muse may read your top artists",
                "code": "relogin_needed",
                "login_url": "/api/v1/auth/login",
            },
        ) from error
    except NotLoggedInError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Your Spotify login has expired; open /api/v1/auth/login again"},
        ) from error
    except SpotifyError as error:
        raise spotify_http_error(error) from error

"""Saving a curated playlist to Spotify, and the history of saved playlists."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, get_playlist_service
from app.api.errors import spotify_http_error
from app.clients.spotify import SpotifyError
from app.schemas.playlists import ExportRequest, PlaylistOut
from app.services.auth import NotLoggedInError
from app.services.playlists import PlaylistService

router = APIRouter(prefix="/playlists", tags=["playlists"])
Service = Annotated[PlaylistService, Depends(get_playlist_service)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Save a curated playlist to your Spotify account (private)",
)
async def export_playlist(body: ExportRequest, user: CurrentUser, service: Service) -> PlaylistOut:
    try:
        record, cover = await service.export(user, body)
    except NotLoggedInError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Your Spotify login has expired; open /api/v1/auth/login again"},
        ) from error
    except SpotifyError as error:
        raise spotify_http_error(error) from error
    return PlaylistOut(**record.model_dump(), cover=cover)


@router.get("", summary="Playlists Muse has saved for you (newest first)")
async def playlist_history(user: CurrentUser, service: Service) -> list[PlaylistOut]:
    return [PlaylistOut(**record.model_dump()) for record in await service.history(user)]

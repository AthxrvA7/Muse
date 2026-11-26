"""30-second song previews (Deezer), for the play button on the website.

The browser's audio player asks for /api/v1/previews/{deezer_id}; Muse fetches a fresh
signed link from Deezer and redirects to it. Links are never stored for long, because
Deezer's expire within minutes (see clients/deezer.py).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import RedirectResponse

from app.clients.deezer import DeezerClient
from app.services.curate import open_deezer

router = APIRouter(prefix="/previews", tags=["previews"])

DeezerId = Annotated[int, Path(gt=0, le=10**12, description="Deezer track ID from a curated track")]


@router.get(
    "/{deezer_id}",
    summary="Play a song's 30-second preview (redirects to Deezer's audio)",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={404: {"description": "No preview for this song"}},
)
async def preview(
    deezer_id: DeezerId, deezer: Annotated[DeezerClient | None, Depends(open_deezer)]
) -> RedirectResponse:
    url = await deezer.preview_url(deezer_id) if deezer else None
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "No preview for this song"},
        )
    # no-store: the link expires soon, so neither the browser nor a proxy may keep it
    return RedirectResponse(url, status_code=307, headers={"Cache-Control": "no-store"})

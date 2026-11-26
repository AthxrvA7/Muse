"""Cover art preview: the same image Muse puts on a saved Spotify playlist."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.core.cache import TTLCache
from app.services.cover import make_cover

router = APIRouter(prefix="/covers", tags=["playlists"])

_covers = TTLCache(seconds=24 * 3600, size=300)  # small JPEGs; the same mood draws the same


@router.get(
    "",
    summary="Preview a playlist cover for a mood (JPEG)",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def cover(
    valence: Annotated[float, Query(ge=0, le=1)],
    energy: Annotated[float, Query(ge=0, le=1)],
    title: Annotated[str, Query(min_length=1, max_length=80)],
    words: Annotated[list[str], Query(max_length=3)] = [],  # noqa: B006 - FastAPI query default
) -> Response:
    title = " ".join(title.split())
    words = [" ".join(w.split())[:20] for w in words if w.strip()]
    key = f"{valence:.2f}|{energy:.2f}|{title}|{'|'.join(words)}"
    jpeg = _covers.get(key)
    if jpeg is None:
        jpeg = await asyncio.to_thread(make_cover, valence, energy, title, words)
        _covers.put(key, jpeg)
    return Response(jpeg, media_type="image/jpeg")  # cached here, so repeats cost nothing

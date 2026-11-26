"""Muse Rewind: a fun, shareable PDF of your moods and music (made on request, never kept)."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, RewindSources, get_rewind_sources
from app.schemas.moods import MAX_DAYS
from app.services.preferences import music_dna
from app.services.recommender.knowledge import get_genre_knowledge
from app.services.rewind import build_rewind
from app.services.rewind_render import rewind_pdf, rewind_preview

router = APIRouter(prefix="/me/rewind", tags=["rewind"])
Sources = Annotated[RewindSources, Depends(get_rewind_sources)]


@router.get(
    "",
    summary="Your Muse Rewind: a colourful PDF of your moods and music to share",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}, "image/jpeg": {}}}},
)
async def rewind(
    user: CurrentUser,
    sources: Sources,
    days: Annotated[int, Query(ge=1, le=MAX_DAYS)] = 30,
    moods: bool = True,
    taste: bool = True,
    learned: bool = True,
    playlists: bool = True,
    tz: Annotated[int, Query(ge=-720, le=840, description="Your UTC offset in minutes")] = 0,
    format: Literal["pdf", "preview"] = "pdf",
) -> Response:
    """Leave out any part with `moods=false`, `taste=false`, `learned=false` or
    `playlists=false`. `format=preview` returns the pages side by side as one small JPEG
    (the page count is in `X-Rewind-Pages`). Nothing is stored or shared by Muse."""
    preferences = await sources.preferences.get(user.id) if taste else None
    report = build_rewind(
        name=user.display_name,
        days=days,
        now=datetime.now(UTC),
        offset_minutes=tz,
        moods=await sources.moods.list_for_user(user.id, days) if moods else None,
        dna=music_dna(preferences, get_genre_knowledge()) if preferences else None,
        ratings=await sources.feedback.list_for_user(user.id) if learned else None,
        playlists=await sources.playlists.list_for_user(user.id, limit=1000) if playlists else None,
    )
    pages = str(len(report.pages))
    if format == "preview":
        image = await run_in_threadpool(rewind_preview, report)
        return Response(image, media_type="image/jpeg", headers={"X-Rewind-Pages": pages})
    pdf = await run_in_threadpool(rewind_pdf, report)
    filename = f"muse-rewind-{datetime.now(UTC):%Y-%m-%d}.pdf"
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Rewind-Pages": pages,
        },
    )

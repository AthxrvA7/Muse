"""Mood trajectory ("Learn from me"): how your moods changed across Muse sessions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUser, get_mood_log_repository
from app.db.repositories.mood_log import MoodLogRepository
from app.schemas.moods import MAX_DAYS, MoodSettings, MoodTrajectory
from app.services.trajectory import summarise

router = APIRouter(prefix="/moods", tags=["moods"])
Repo = Annotated[MoodLogRepository, Depends(get_mood_log_repository)]


@router.get("/trajectory", summary="Your moods over time (numbers and mood words only)")
async def trajectory(
    user: CurrentUser,
    repo: Repo,
    days: Annotated[int, Query(ge=1, le=MAX_DAYS)] = 30,
) -> MoodTrajectory:
    """One point per playlist you curated with the trajectory on. Mood text is never kept."""
    result = summarise(await repo.list_for_user(user.id, days), days)
    return result.model_copy(update={"enabled": await repo.is_enabled(user.id)})


@router.put(
    "/settings",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Turn the mood trajectory on or off (off by default)",
)
async def settings(body: MoodSettings, user: CurrentUser, repo: Repo) -> Response:
    await repo.set_enabled(user.id, body.enabled)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Clear your mood history")
async def clear(user: CurrentUser, repo: Repo) -> Response:
    await repo.delete_all(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

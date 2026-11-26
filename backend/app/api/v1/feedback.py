"""👍/👎 on songs: Muse learns from them for your next playlists ("Learn from me")."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUser, get_feedback_repository
from app.db.repositories.feedback import FeedbackRepository
from app.schemas.feedback import FeedbackIn, LearnedSummary
from app.services.learning import summarise

router = APIRouter(prefix="/feedback", tags=["feedback"])
Repo = Annotated[FeedbackRepository, Depends(get_feedback_repository)]


@router.put(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Rate a song: 1 = 👍, -1 = 👎, 0 = take your rating back",
)
async def rate(body: FeedbackIn, user: CurrentUser, repo: Repo) -> Response:
    await repo.rate(user.id, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", summary="What Muse has learned from your ratings")
async def learned(user: CurrentUser, repo: Repo) -> LearnedSummary:
    return summarise(await repo.list_for_user(user.id))


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Forget everything Muse learned from your ratings",
)
async def forget(user: CurrentUser, repo: Repo) -> Response:
    await repo.delete_all(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

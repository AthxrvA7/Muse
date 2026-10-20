"""Mood endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.mood import MoodProfile, MoodRequest
from app.services.mood import get_mood_analyzer
from app.services.mood.analyzer import MoodAnalyzer, UnknownChipError

router = APIRouter(prefix="/mood", tags=["mood"])


@router.post("/analyze", summary="Turn a mood into music characteristics")
def analyze_mood(
    request: MoodRequest,
    analyzer: Annotated[MoodAnalyzer, Depends(get_mood_analyzer)],
) -> MoodProfile:
    """Send mood chips and/or a sentence. Nothing you send here is stored or logged."""
    try:
        return analyzer.analyze(request)
    except UnknownChipError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": str(error), "allowed_chips": error.allowed},
        ) from error

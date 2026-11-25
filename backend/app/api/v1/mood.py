"""Mood endpoints."""

from typing import Annotated, get_args

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.mood import (
    MAX_CHIPS,
    MAX_TEXT_LENGTH,
    ChipOption,
    Mode,
    MoodOptions,
    MoodProfile,
    MoodRequest,
)
from app.services.mood import get_mood_analyzer
from app.services.mood.analyzer import MoodAnalyzer, UnknownChipError
from app.services.mood.vocabulary import get_vocabulary

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


@router.get("/options", summary="Mood chips and modes a client can offer")
def mood_options() -> MoodOptions:
    vocabulary = get_vocabulary()
    return MoodOptions(
        chips=[
            ChipOption(id=chip_id, valence=chip.valence, energy=chip.energy)
            for chip_id, chip in sorted(vocabulary.chips.items())
        ],
        modes=list(get_args(Mode)),
        max_chips=MAX_CHIPS,
        max_text_length=MAX_TEXT_LENGTH,
    )

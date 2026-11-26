"""Mood trajectory: how a user's moods changed across their Muse sessions.

Only the mood's two numbers, its mood words (from Muse's fixed list) and the playlist
mode are kept, never the text the user typed.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.mood import Mode

MAX_DAYS = 90  # mood history is kept this long (TTL index)


class MoodEntry(BaseModel):
    at: datetime
    valence: float = Field(ge=0, le=1, description="0 = very negative, 1 = very positive")
    energy: float = Field(ge=0, le=1, description="0 = very calm, 1 = very intense")
    labels: list[str] = Field(description="Mood words from Muse's fixed list")
    mode: Mode


class LabelCount(BaseModel):
    label: str
    count: int


class MoodAverage(BaseModel):
    valence: float
    energy: float


class MoodTrajectory(BaseModel):
    enabled: bool = Field(default=True, description="Whether new moods are being kept (opt-in)")
    days: int = Field(description="How far back this looks")
    points: list[MoodEntry] = Field(description="Oldest first")
    average: MoodAverage | None = Field(description="null when there are no points")
    top_labels: list[LabelCount] = Field(description="The most frequent mood words (up to 3)")
    brightness: Literal["lighter", "heavier", "steady"] | None = Field(
        description="Recent half compared with the earlier half; null with fewer than 4 points"
    )
    energy: Literal["more energetic", "calmer", "steady"] | None = Field(
        description="Recent half compared with the earlier half; null with fewer than 4 points"
    )


class MoodSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(description="Keep a mood trajectory from now on")

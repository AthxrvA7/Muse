"""👍/👎 on a curated song: what Muse remembers so the next playlist fits better."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: str = Field(description="Spotify track ID from a curated playlist")
    value: Literal[1, -1, 0] = Field(description="1 = 👍, -1 = 👎, 0 = take it back")
    artist_ids: list[str] = Field(default=[], max_length=5)
    artist_names: list[str] = Field(default=[], max_length=5)
    genre: str | None = Field(default=None, max_length=40)
    language: str | None = Field(default=None, max_length=5)
    valence: float | None = Field(default=None, ge=0, le=1, description="The mood it was rated in")
    energy: float | None = Field(default=None, ge=0, le=1)

    @field_validator("track_id")
    @classmethod
    def _track_id(cls, value: str) -> str:
        if not value.isalnum() or len(value) != 22:
            raise ValueError("track_id must be a Spotify track ID (22 letters/digits)")
        return value

    @field_validator("artist_ids")
    @classmethod
    def _artist_ids(cls, ids: list[str]) -> list[str]:
        if any(not i.isalnum() or len(i) > 40 for i in ids):
            raise ValueError("artist_ids must be Spotify artist IDs")
        return ids

    @field_validator("artist_names")
    @classmethod
    def _names(cls, names: list[str]) -> list[str]:
        return [" ".join(n.split())[:100] for n in names if n.strip()]


class FeedbackRecord(FeedbackIn):
    """A stored rating (value is never 0: taking a rating back deletes it)."""

    model_config = ConfigDict(extra="ignore")

    user_id: str
    updated_at: datetime


class ArtistCount(BaseModel):
    name: str
    count: int


class LearnedSummary(BaseModel):
    """What Muse has learned from your ratings (shown on the website)."""

    likes: int
    dislikes: int
    liked_artists: list[ArtistCount]
    avoided_artists: list[ArtistCount]
    ratings: dict[str, int] = Field(description="track ID -> 1 or -1, to show your ratings")

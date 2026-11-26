"""Saving a curated playlist to the user's Spotify account."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CoverRequest(BaseModel):
    """What the cover art shows: the mood's colour and energy, a headline, mood words."""

    model_config = ConfigDict(extra="forbid")

    valence: float = Field(ge=0, le=1)
    energy: float = Field(ge=0, le=1)
    title: str = Field(min_length=1, max_length=80)
    words: list[str] = Field(default=[], max_length=3)

    @field_validator("title")
    @classmethod
    def _one_line(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("words")
    @classmethod
    def _short_words(cls, words: list[str]) -> list[str]:
        return [" ".join(w.split())[:20] for w in words if w.strip()]


class ExportRequest(BaseModel):
    """Send back the track IDs from a POST /curate preview."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Muse: tired and low",
                    # Placeholders on purpose: real IDs here would add unrelated songs
                    # when someone runs the example in Swagger. Paste IDs from /curate.
                    "track_ids": ["paste-tracks[].track.id-from-POST-/curate"],
                }
            ]
        },
    )

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="Curated by Muse for how you felt.", max_length=300)
    track_ids: list[str] = Field(
        min_length=1,
        max_length=100,
        description="Spotify track IDs from a POST /curate response (tracks[].track.id)",
    )
    cover: CoverRequest | None = Field(
        default=None, description="Add Muse's cover art, painted from the mood (optional)"
    )

    @field_validator("name", "description")
    @classmethod
    def _single_line(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("track_ids")
    @classmethod
    def _check_ids(cls, ids: list[str]) -> list[str]:
        for track_id in ids:
            if not track_id.isalnum() or len(track_id) != 22:
                raise ValueError("track_ids must be Spotify track IDs (22 letters/digits)")
        return list(dict.fromkeys(ids))  # duplicates removed, order kept


class PlaylistOut(BaseModel):
    id: str
    spotify_playlist_id: str
    url: str = Field(description="Open this to see the playlist in Spotify")
    name: str
    track_count: int
    created_at: datetime
    cover: Literal["added", "needs_login", "failed", "none"] = Field(
        default="none",
        description="added · needs_login (log in again to allow covers) · failed (the "
        "playlist is fine, the cover isn't) · none (not asked for)",
    )

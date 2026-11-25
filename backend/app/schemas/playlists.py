"""Saving a curated playlist to the user's Spotify account."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExportRequest(BaseModel):
    """Send back the track IDs from a POST /curate preview."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Muse: tired and low",
                    "track_ids": ["4uLU6hMCjMI75M1A2tKUQC", "7ouMYWpwJ422jRcDASZB7P"],
                }
            ]
        },
    )

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="Curated by Muse for how you felt.", max_length=300)
    track_ids: list[str] = Field(min_length=1, max_length=100)

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

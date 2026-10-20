"""Request and response models for curation (mood + taste -> ranked playlist)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalog import Track
from app.schemas.mood import MoodProfile, MoodRequest

MAX_NAME_LENGTH = 100


def _unique(values: list[str], *, lowercase: bool) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        clean = " ".join(value.split())[:MAX_NAME_LENGTH]
        key = clean.lower()
        if clean and key not in seen:
            seen[key] = key if lowercase else clean
    return list(seen.values())


class Taste(BaseModel):
    """What the user says they like. Everything is optional."""

    model_config = ConfigDict(extra="forbid")

    artists: list[str] = Field(
        default=[], max_length=10, examples=[["Prateek Kuhad", "Arijit Singh"]]
    )
    genres: list[str] = Field(default=[], max_length=10, examples=[["indie folk", "bollywood"]])
    languages: list[str] = Field(default=[], max_length=5, examples=[["hi", "en"]])
    exclude_artists: list[str] = Field(default=[], max_length=20)
    allow_explicit: bool = True

    @field_validator("artists", "exclude_artists")
    @classmethod
    def _clean_names(cls, names: list[str]) -> list[str]:
        return _unique(names, lowercase=False)

    @field_validator("genres", "languages")
    @classmethod
    def _clean_ids(cls, ids: list[str]) -> list[str]:
        return _unique(ids, lowercase=True)


class CurateRequest(BaseModel):
    """How the user feels + what they like -> a playlist preview."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "mood": {"chips": ["tired", "low"], "text": "long day, want something soft"},
                    "taste": {
                        "artists": ["Prateek Kuhad", "Arijit Singh"],
                        "genres": ["indie folk", "bollywood"],
                        "languages": ["hi", "en"],
                    },
                    "size": 15,
                }
            ]
        },
    )

    mood: MoodRequest
    taste: Taste = Taste()
    size: int = Field(default=15, ge=10, le=30, description="Number of tracks (10-30)")


class CuratedTrack(BaseModel):
    track: Track
    score: float = Field(description="Overall fit, 0-1")
    mood_fit: float = Field(description="How close the track's feel is to the mood, 0-1")
    taste_fit: float = Field(description="How well it matches the stated taste, 0-1")
    reason: str


class CuratePreview(BaseModel):
    mood: MoodProfile
    tracks: list[CuratedTrack]
    searches: int = Field(description="Spotify searches planned")
    candidates_considered: int
    note: str | None = Field(
        default=None, description="Set when fewer tracks than asked were found"
    )


class GenreOption(BaseModel):
    id: str
    name: str
    languages: list[str]


class TasteOptions(BaseModel):
    """What can go in `taste.genres` and `taste.languages`."""

    genres: list[GenreOption]
    languages: dict[str, str]

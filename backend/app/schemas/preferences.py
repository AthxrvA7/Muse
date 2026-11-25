"""The user's saved taste profile and its Music DNA summary."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.curate import _unique


class PreferencesIn(BaseModel):
    """What the user tells Muse about their taste. Only stated preferences, never history."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "artists": ["Prateek Kuhad", "Arijit Singh", "Anuv Jain"],
                    "genres": ["indie folk", "bollywood", "lo-fi"],
                    "languages": ["hi", "en"],
                    "styles": ["acoustic", "soft vocals"],
                    "reference_tracks": [],
                    "exclusions": [],
                }
            ]
        },
    )

    artists: list[str] = Field(default=[], max_length=10)
    genres: list[str] = Field(default=[], max_length=10, description="See GET /curate/options")
    languages: list[str] = Field(default=[], max_length=5, description="e.g. hi, en")
    styles: list[str] = Field(default=[], max_length=10, description="Free words, e.g. acoustic")
    reference_tracks: list[str] = Field(
        default=[], max_length=10, description="Spotify track IDs that sum up your taste"
    )
    exclusions: list[str] = Field(default=[], max_length=20, description="Artists to never pick")

    @field_validator("artists", "styles", "exclusions")
    @classmethod
    def _clean_names(cls, names: list[str]) -> list[str]:
        return _unique(names, lowercase=False)

    @field_validator("genres", "languages")
    @classmethod
    def _clean_ids(cls, ids: list[str]) -> list[str]:
        return _unique(ids, lowercase=True)

    @field_validator("reference_tracks")
    @classmethod
    def _check_track_ids(cls, ids: list[str]) -> list[str]:
        for track_id in ids:
            if not track_id.isalnum() or len(track_id) != 22:
                raise ValueError("reference_tracks must be Spotify track IDs (22 letters/digits)")
        return list(dict.fromkeys(ids))


class PreferencesOut(PreferencesIn):
    updated_at: datetime | None = None


class GenreInDNA(BaseModel):
    id: str
    name: str
    valence: float
    energy: float


class LanguageInDNA(BaseModel):
    code: str
    name: str


class MoodCentre(BaseModel):
    valence: float
    energy: float
    label: str  # e.g. "calm and warm"


class MusicDNA(BaseModel):
    """A summary of the user's *stated* taste, for the dashboard (FR3)."""

    summary: str
    top_artists: list[str]
    genres: list[GenreInDNA]
    languages: list[LanguageInDNA]
    styles: list[str]
    mood_centre: MoodCentre | None = Field(
        description="Average feel of your genres on the valence-energy map (None without genres)"
    )
    reference_track_count: int
    exclusion_count: int

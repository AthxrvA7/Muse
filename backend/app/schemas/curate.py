"""Request and response models for curation (mood + taste -> ranked playlist)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalog import Track
from app.schemas.mood import MoodProfile, MoodRequest, Tempo

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
    taste: Taste | None = Field(
        default=None,
        description="Leave out to use your saved taste profile (when logged in)",
    )
    size: int = Field(default=15, ge=10, le=30, description="Number of tracks (10-30)")
    familiarity: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Share of songs you already know: 0 = all new, 1 = all familiar. "
        "Leave out for the mode's default (comfort 0.7, focus/energy 0.6, discovery 0.3)",
    )
    language: str = Field(
        default="auto",
        description="auto: one language, chosen from your songs and taste · mix: any "
        "language · or a code such as hi or en (see GET /curate/options)",
    )
    genre: str | None = Field(
        default=None,
        description="Keep the playlist around this genre (see GET /curate/options); "
        "leave out to let Muse choose one",
    )
    exclude_track_ids: list[str] = Field(
        default=[],
        max_length=100,
        description="Spotify track IDs to leave out, e.g. the last playlist (Give me another)",
    )

    @field_validator("exclude_track_ids")
    @classmethod
    def _check_track_ids(cls, ids: list[str]) -> list[str]:
        if any(not track_id.isalnum() or len(track_id) > 40 for track_id in ids):
            raise ValueError("exclude_track_ids must be Spotify track IDs")
        return list(dict.fromkeys(ids))


class CuratedTrack(BaseModel):
    track: Track
    score: float = Field(description="Overall fit, 0-1")
    mood_fit: float = Field(description="How close the track's feel is to the mood, 0-1")
    taste_fit: float = Field(description="How well it matches the stated taste, 0-1")
    reason: str
    known: bool = Field(
        default=False, description="You already play it, or it's by a favourite artist"
    )
    tags: list[str] = Field(default=[], description="Last.fm listener tags about its feel")
    bpm: float | None = Field(default=None, description="Tempo in beats per minute (Deezer)")
    tempo: Tempo | None = Field(default=None, description="slow < 95 BPM ≤ medium ≤ 125 < fast")
    genre: str | None = Field(default=None, description="The song's genre, when known")
    genre_id: str | None = Field(default=None, description="Its genre's ID (send it with a 👍/👎)")
    preview_id: int | None = Field(
        default=None,
        description="Play a 30-second preview at GET /api/v1/previews/{preview_id} (Deezer)",
    )
    language: str | None = Field(default=None, description="The song's language, when known")


class Coverage(BaseModel):
    """How much Muse knew about the songs it considered (for transparency and debugging)."""

    candidates: int = 0
    with_mood: int = Field(default=0, description="Songs with a mood from listener tags")
    with_language: int = Field(default=0, description="Songs whose language Muse could tell")
    with_genre: int = Field(default=0, description="Songs whose genre Muse could tell")
    with_tempo: int = Field(default=0, description="Songs with a BPM from Deezer")


class CuratePreview(BaseModel):
    mood: MoodProfile
    tracks: list[CuratedTrack]
    searches: int = Field(description="Spotify searches planned")
    candidates_considered: int
    taste_source: Literal["request", "saved_profile", "none"] = Field(
        default="request", description="Where the taste used for this playlist came from"
    )
    note: str | None = Field(
        default=None, description="Set when fewer tracks than asked were found"
    )
    familiarity: float = Field(default=0.0, description="Share of known songs aimed for")
    personal: bool = Field(
        default=False, description="Your Spotify top tracks were used as familiar songs"
    )
    mood_data: Literal["lastfm", "estimated"] = Field(
        default="estimated",
        description="lastfm: song moods from Last.fm listener tags; estimated: from genres",
    )
    similar_artists: list[str] = Field(
        default=[], description="Artists similar to your favourites that Muse searched"
    )
    language: str | None = Field(
        default=None, description="The playlist's language (None: mixed or unknown)"
    )
    genre: str | None = Field(default=None, description="The genre the playlist is built around")
    coverage: Coverage = Field(default_factory=Coverage)
    learned_from: int = Field(default=0, description="How many of your 👍/👎 shaped this playlist")


class GenreOption(BaseModel):
    id: str
    name: str
    languages: list[str]


class TasteOptions(BaseModel):
    """What can go in `taste.genres` and `taste.languages`."""

    genres: list[GenreOption]
    languages: dict[str, str]

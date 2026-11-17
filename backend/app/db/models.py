"""Documents stored in MongoDB.

MongoDB has no fixed schema, so these Pydantic models are the schema contract.
Every document also carries ``schema_version`` so a future change can be migrated
with a small numbered script (see ARCHITECTURE §5).

Only Muse-owned data lives here: what the user told Muse and what Muse generated.
Free-text mood input is never stored.
"""

from datetime import datetime

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class User(BaseModel):
    id: str
    spotify_id: str
    display_name: str | None = None
    created_at: datetime
    last_login_at: datetime


class Session(BaseModel):
    """One logged-in browser. Only the SHA-256 hash of the session ID is stored."""

    id_hash: str
    user_id: str
    created_at: datetime
    last_seen_at: datetime


class Preferences(BaseModel):
    """A user's stated taste: only what they told Muse, never their Spotify history."""

    user_id: str
    artists: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    reference_tracks: list[str] = Field(default_factory=list)  # Spotify track IDs
    exclusions: list[str] = Field(default_factory=list)  # artists or genres to leave out
    updated_at: datetime

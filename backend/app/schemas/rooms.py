"""Room mode: a class or a group shares its mood live, for presentations and parties.

People join with a short code, tap up to three mood chips (no free text, no login),
and the screen shows the room's mood map. Rooms live in memory for a few hours.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.moods import LabelCount, MoodAverage


class VoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voter: str = Field(
        pattern=r"^[A-Za-z0-9_-]{8,40}$", description="A random ID the phone keeps for this room"
    )
    chips: list[str] = Field(min_length=1, max_length=3, description="Up to 3 mood chips")

    @field_validator("chips")
    @classmethod
    def _normalise(cls, chips: list[str]) -> list[str]:
        return list(dict.fromkeys(c.strip().lower() for c in chips if c.strip()))


class RoomPoint(BaseModel):
    valence: float
    energy: float
    labels: list[str]


class RoomPersonality(BaseModel):
    name: str
    line: str


class RoomCreated(BaseModel):
    code: str = Field(description="Share this: people join at /app/#/join/<code>")


class RoomSummary(BaseModel):
    code: str
    voters: int
    chips: list[LabelCount] = Field(description="Every mood chip picked, most picked first")
    points: list[RoomPoint] = Field(description="One point per person, oldest first")
    average: MoodAverage | None
    personality: RoomPersonality | None
    locked: bool = Field(default=False, description="Locked rooms take no new voters")


class LockIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    locked: bool

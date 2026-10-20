"""Request and response models for mood analysis."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# How the playlist should feel overall:
#   comfort   - stay close to the mood and the user's known taste (default)
#   focus     - steady, mid-energy music for studying or working
#   energy    - lift the energy (gym, party)
#   discovery - lean towards the mood and new music over known favourites
Mode = Literal["comfort", "focus", "energy", "discovery"]
Tempo = Literal["slow", "medium", "fast"]

MAX_CHIPS = 5
MAX_TEXT_LENGTH = 500


class MoodRequest(BaseModel):
    """How the user feels: mood chips, a sentence, or both."""

    model_config = ConfigDict(extra="forbid")

    chips: list[str] = Field(default=[], max_length=MAX_CHIPS, examples=[["tired", "low"]])
    text: str | None = Field(
        default=None,
        max_length=MAX_TEXT_LENGTH,
        examples=["long day, want something soft but not depressing"],
    )
    mode: Mode | None = Field(
        default=None, description="Optional; detected from the text if left out"
    )

    @field_validator("chips")
    @classmethod
    def _normalise_chips(cls, chips: list[str]) -> list[str]:
        # lowercase, trimmed, duplicates removed, order kept
        return list(dict.fromkeys(c.strip().lower() for c in chips if c.strip()))

    @field_validator("text")
    @classmethod
    def _blank_text_is_no_text(cls, text: str | None) -> str | None:
        return text.strip() or None if text else None

    @model_validator(mode="after")
    def _needs_chips_or_text(self) -> "MoodRequest":
        if not self.chips and not self.text:
            raise ValueError("Send at least one mood chip or some text")
        return self


class SupportNotice(BaseModel):
    """A kind message and where to find help, shown when the text suggests distress."""

    message: str
    resources: list[dict[str, str]]


class MoodProfile(BaseModel):
    """The mood expressed as numbers Muse can rank music with."""

    valence: float = Field(ge=0, le=1, description="0 = very negative, 1 = very positive")
    energy: float = Field(ge=0, le=1, description="0 = very calm, 1 = very intense")
    tempo: Tempo
    mode: Mode
    labels: list[str] = Field(description="The moods and emotions that shaped this profile")
    confidence: float = Field(ge=0, le=1, description="How sure Muse is about this reading")
    text_analysis: Literal["classifier", "keywords"] | None = Field(
        description="How the free text was read, or null if no text was sent"
    )
    support: SupportNotice | None = Field(
        default=None, description="Present only if the text suggests the person may be struggling"
    )

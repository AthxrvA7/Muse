"""Loads and validates Muse's mood vocabulary (``app/knowledge/mood_map.json``).

The vocabulary is application-owned data: every mood chip, emotion and intent
word Muse understands, with its position on the valence-energy plane.
Validation runs once at startup, so a typo in the JSON fails fast and loudly.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"
DEFAULT_VOCABULARY_PATH = KNOWLEDGE_DIR / "mood_map.json"

# A number between 0 and 1 (inclusive)
Unit = Annotated[float, Field(ge=0.0, le=1.0)]


class MoodPoint(BaseModel):
    """A point on Russell's circumplex: valence (negative to positive), energy (calm to intense)."""

    valence: Unit
    energy: Unit


class Chip(MoodPoint):
    synonyms: list[str] = []

    @field_validator("synonyms")
    @classmethod
    def _lowercase(cls, words: list[str]) -> list[str]:
        return [w.strip().lower() for w in words]


class MoodVocabulary(BaseModel):
    version: int
    about: str
    chips: dict[str, Chip]
    emotions: dict[str, MoodPoint]
    intents: dict[str, list[str]]

    @model_validator(mode="after")
    def _no_word_means_two_moods(self) -> "MoodVocabulary":
        seen: dict[str, str] = {}
        for chip_id, chip in self.chips.items():
            for word in [chip_id, *chip.synonyms]:
                if word in seen:
                    raise ValueError(f"'{word}' is used by both '{seen[word]}' and '{chip_id}'")
                seen[word] = chip_id
        return self

    @property
    def chip_ids(self) -> list[str]:
        return sorted(self.chips)


def load_vocabulary(path: Path = DEFAULT_VOCABULARY_PATH) -> MoodVocabulary:
    return MoodVocabulary.model_validate_json(path.read_text(encoding="utf-8"))


@lru_cache
def get_vocabulary() -> MoodVocabulary:
    """The vocabulary, loaded once per process."""
    return load_vocabulary()

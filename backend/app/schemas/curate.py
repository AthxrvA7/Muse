"""Request and response models for curation (mood + taste -> ranked playlist)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

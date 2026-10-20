"""Loads and validates Muse's genre knowledge base (``app/knowledge/genre_kb.json``).

Spotify no longer tells apps how energetic or positive a track is, and artist
genres usually come back empty (ADR-0002). This file is Muse's own answer:
where each genre typically sits on the valence-energy plane, which languages
it belongs to, and how to search Spotify for it.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from app.services.mood.vocabulary import KNOWLEDGE_DIR, MoodPoint

DEFAULT_GENRE_KB_PATH = KNOWLEDGE_DIR / "genre_kb.json"


class Genre(MoodPoint):
    name: str
    langs: list[str]
    spotify_genre: str = Field(min_length=1)
    keywords: str = Field(min_length=1)


class GenreKnowledge(BaseModel):
    version: int
    about: str
    languages: dict[str, str]
    genres: dict[str, Genre]

    @model_validator(mode="after")
    def _languages_are_known(self) -> "GenreKnowledge":
        for genre_id, genre in self.genres.items():
            unknown = set(genre.langs) - set(self.languages)
            if unknown:
                raise ValueError(f"Genre '{genre_id}' uses unknown language(s): {sorted(unknown)}")
        return self

    def genres_for_languages(self, languages: list[str]) -> list[str]:
        """Genre ids sung in any of these languages (language-neutral genres excluded)."""
        wanted = set(languages)
        return [gid for gid, g in self.genres.items() if wanted & set(g.langs)]


def load_genre_knowledge(path: Path = DEFAULT_GENRE_KB_PATH) -> GenreKnowledge:
    return GenreKnowledge.model_validate_json(path.read_text(encoding="utf-8"))


@lru_cache
def get_genre_knowledge() -> GenreKnowledge:
    return load_genre_knowledge()

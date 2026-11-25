"""Loads and validates Muse's genre knowledge base (``app/knowledge/genre_kb.json``).

Spotify no longer tells apps how energetic or positive a track is, and artist
genres usually come back empty (ADR-0002). This file is Muse's own answer:
where each genre typically sits on the valence-energy plane, which languages
it belongs to, and how to search Spotify for it.
"""

import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from app.services.mood.vocabulary import KNOWLEDGE_DIR, MoodPoint

DEFAULT_GENRE_KB_PATH = KNOWLEDGE_DIR / "genre_kb.json"


class Genre(MoodPoint):
    name: str
    langs: list[str]
    family: str  # the scene it belongs to, e.g. "indian film & pop"
    spotify_genre: str = Field(min_length=1)
    keywords: str = Field(min_length=1)


class GenreKnowledge(BaseModel):
    version: int
    about: str
    languages: dict[str, str]
    genres: dict[str, Genre]
    related_families: dict[str, list[str]] = {}  # families that blend well together

    @model_validator(mode="after")
    def _languages_are_known(self) -> "GenreKnowledge":
        for genre_id, genre in self.genres.items():
            unknown = set(genre.langs) - set(self.languages)
            if unknown:
                raise ValueError(f"Genre '{genre_id}' uses unknown language(s): {sorted(unknown)}")
        families = {genre.family for genre in self.genres.values()}
        for family, related in self.related_families.items():
            unknown = ({family} | set(related)) - families
            if unknown:
                raise ValueError(f"related_families uses unknown family(ies): {sorted(unknown)}")
        return self

    def coherence(self, genre_id: str | None, anchor_id: str | None) -> float:
        """How well a genre sits in a playlist anchored on another genre (0-1).

        Same genre 1.0 · same family 0.85 · related family 0.55 · unrelated 0 ·
        unknown 0.5 (no evidence either way).
        """
        if (
            not genre_id
            or not anchor_id
            or genre_id not in self.genres
            or anchor_id not in self.genres
        ):
            return 0.5
        if genre_id == anchor_id:
            return 1.0
        family, anchor = self.genres[genre_id].family, self.genres[anchor_id].family
        if family == anchor:
            return 0.85
        if family in self.related_families.get(anchor, []) or anchor in self.related_families.get(
            family, []
        ):
            return 0.55
        return 0.0

    def genres_for_languages(self, languages: list[str]) -> list[str]:
        """Genre ids sung in any of these languages (language-neutral genres excluded)."""
        wanted = set(languages)
        return [gid for gid, g in self.genres.items() if wanted & set(g.langs)]


def load_genre_knowledge(path: Path = DEFAULT_GENRE_KB_PATH) -> GenreKnowledge:
    return GenreKnowledge.model_validate_json(path.read_text(encoding="utf-8"))


@lru_cache
def get_genre_knowledge() -> GenreKnowledge:
    return load_genre_knowledge()


def match_genre(name: str, kb: GenreKnowledge) -> str | None:
    """Map a Spotify or Last.fm genre ("modern bollywood") to a genre Muse knows ("bollywood")."""
    name = " ".join(name.lower().split())
    if name in kb.genres:
        return name
    for genre_id, genre in kb.genres.items():
        if genre.spotify_genre.lower() == name:
            return genre_id
    # Longest known genre contained as whole words: "indie pop" beats "pop"
    contained = [g for g in kb.genres if re.search(rf"(?<![\w-]){re.escape(g)}(?![\w-])", name)]
    return max(contained, key=len) if contained else None

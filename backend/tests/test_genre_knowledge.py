"""The genre knowledge base must load and make sense."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.recommender.knowledge import DEFAULT_GENRE_KB_PATH, load_genre_knowledge


def test_knowledge_base_loads_with_enough_genres() -> None:
    kb = load_genre_knowledge()

    assert len(kb.genres) >= 50
    assert {"en", "hi", "pa", "mr"} <= set(kb.languages)


def test_genres_cover_all_four_quadrants() -> None:
    genres = load_genre_knowledge().genres.values()

    assert any(g.valence > 0.5 and g.energy > 0.5 for g in genres)  # e.g. dance pop
    assert any(g.valence > 0.5 and g.energy < 0.5 for g in genres)  # e.g. lo-fi
    assert any(g.valence < 0.5 and g.energy < 0.5 for g in genres)  # e.g. ghazal
    assert any(g.valence < 0.5 and g.energy > 0.5 for g in genres)  # e.g. metal


def test_every_language_has_at_least_one_genre() -> None:
    kb = load_genre_knowledge()

    for code in kb.languages:
        assert kb.genres_for_languages([code]), f"no genre for language {code}"


def test_language_lookup_returns_matching_genres_only() -> None:
    kb = load_genre_knowledge()

    hindi = kb.genres_for_languages(["hi"])

    assert "bollywood" in hindi
    assert "k-pop" not in hindi
    assert "lo-fi" not in hindi  # language-neutral genres are not language matches


def test_unknown_language_codes_are_rejected(tmp_path: Path) -> None:
    data = json.loads(DEFAULT_GENRE_KB_PATH.read_text(encoding="utf-8"))
    data["genres"]["pop"]["langs"] = ["xx"]
    path = tmp_path / "genre_kb.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValidationError, match="unknown language"):
        load_genre_knowledge(path)

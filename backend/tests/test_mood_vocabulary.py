"""The mood vocabulary file must load and make sense."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.mood.vocabulary import DEFAULT_VOCABULARY_PATH, load_vocabulary


def test_vocabulary_file_loads() -> None:
    vocabulary = load_vocabulary()

    assert len(vocabulary.chips) >= 15
    assert set(vocabulary.emotions) == {"joy", "love", "surprise", "sadness", "anger", "fear"}
    assert set(vocabulary.intents) == {"focus", "energy", "sleep", "discovery"}


def test_chips_cover_all_four_quadrants_of_the_circumplex() -> None:
    chips = load_vocabulary().chips.values()

    assert any(c.valence > 0.5 and c.energy > 0.5 for c in chips)  # happy, excited
    assert any(c.valence > 0.5 and c.energy < 0.5 for c in chips)  # calm, content
    assert any(c.valence < 0.5 and c.energy < 0.5 for c in chips)  # sad, tired
    assert any(c.valence < 0.5 and c.energy > 0.5 for c in chips)  # anxious, angry


def _write(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "mood_map.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_values_outside_zero_to_one_are_rejected(tmp_path: Path) -> None:
    data = json.loads(DEFAULT_VOCABULARY_PATH.read_text(encoding="utf-8"))
    data["chips"]["happy"]["valence"] = 1.5

    with pytest.raises(ValidationError):
        load_vocabulary(_write(tmp_path, data))


def test_a_word_cannot_belong_to_two_moods(tmp_path: Path) -> None:
    data = json.loads(DEFAULT_VOCABULARY_PATH.read_text(encoding="utf-8"))
    data["chips"]["calm"]["synonyms"].append("sad")  # already a synonym of "low"

    with pytest.raises(ValidationError, match="'sad' is used by both"):
        load_vocabulary(_write(tmp_path, data))

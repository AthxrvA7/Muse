"""Unit tests for the mood analyzer (no HTTP)."""

import pytest

from app.schemas.mood import MoodRequest
from app.services.mood.analyzer import MoodAnalyzer, UnknownChipError, tempo_for
from app.services.mood.vocabulary import load_vocabulary


@pytest.fixture(scope="module")
def analyzer() -> MoodAnalyzer:
    return MoodAnalyzer(load_vocabulary())


def test_single_chip_maps_to_its_point(analyzer: MoodAnalyzer) -> None:
    profile = analyzer.analyze(MoodRequest(chips=["calm"]))

    assert (profile.valence, profile.energy) == (0.65, 0.20)
    assert profile.tempo == "slow"
    assert profile.labels == ["calm"]
    assert profile.text_analysis is None


def test_several_chips_are_averaged(analyzer: MoodAnalyzer) -> None:
    profile = analyzer.analyze(MoodRequest(chips=["tired", "low"]))  # (0.40,0.15) and (0.22,0.25)

    assert profile.valence == pytest.approx(0.31)
    assert profile.energy == pytest.approx(0.20)


def test_unknown_chip_is_rejected_with_the_allowed_list(analyzer: MoodAnalyzer) -> None:
    with pytest.raises(UnknownChipError) as error:
        analyzer.analyze(MoodRequest(chips=["happy", "hangry"]))

    assert error.value.unknown == ["hangry"]
    assert "happy" in error.value.allowed


def test_mood_words_in_text_are_recognised(analyzer: MoodAnalyzer) -> None:
    profile = analyzer.analyze(MoodRequest(text="Feeling really drained after work"))

    assert profile.labels == ["tired"]
    assert profile.text_analysis == "keywords"


def test_negated_mood_words_are_ignored(analyzer: MoodAnalyzer) -> None:
    profile = analyzer.analyze(MoodRequest(text="I'm not happy today, honestly a bit sad"))

    assert "happy" not in profile.labels
    assert "low" in profile.labels


def test_text_without_mood_words_is_neutral_with_low_confidence(analyzer: MoodAnalyzer) -> None:
    profile = analyzer.analyze(MoodRequest(text="what should I play"))

    assert (profile.valence, profile.energy) == (0.5, 0.5)
    assert profile.labels == ["neutral"]
    assert profile.confidence < 0.5
    assert profile.text_analysis == "keywords"


def test_chips_weigh_more_than_text(analyzer: MoodAnalyzer) -> None:
    # chip "happy" (0.85) + text saying "sad" (0.22): result stays closer to happy
    profile = analyzer.analyze(MoodRequest(chips=["happy"], text="kind of sad"))

    assert profile.valence > 0.5
    assert profile.labels == ["happy", "low"]


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("need music to study", "focus"),
        ("heading to the gym", "energy"),
        ("want to discover something new", "discovery"),
        ("just had a long day", "comfort"),
    ],
)
def test_intent_words_pick_the_mode(analyzer: MoodAnalyzer, text: str, mode: str) -> None:
    assert analyzer.analyze(MoodRequest(text=text)).mode == mode


def test_focus_mode_keeps_energy_steady(analyzer: MoodAnalyzer) -> None:
    profile = analyzer.analyze(MoodRequest(chips=["hyped"], mode="focus"))

    assert 0.30 <= profile.energy <= 0.55


def test_energy_mode_lifts_the_energy(analyzer: MoodAnalyzer) -> None:
    assert analyzer.analyze(MoodRequest(chips=["tired"], mode="energy")).energy >= 0.75


def test_sleep_intent_brings_energy_down(analyzer: MoodAnalyzer) -> None:
    profile = analyzer.analyze(MoodRequest(chips=["happy"], text="something to fall asleep to"))

    assert profile.energy <= 0.20
    assert profile.mode == "comfort"


@pytest.mark.parametrize(("energy", "tempo"), [(0.1, "slow"), (0.5, "medium"), (0.9, "fast")])
def test_tempo_follows_energy(energy: float, tempo: str) -> None:
    assert tempo_for(energy) == tempo

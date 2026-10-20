"""Loading the emotion model safely, and using it for free text."""

import json
import logging
from pathlib import Path

import pytest

from app.schemas.mood import MoodRequest
from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.classifier import CARD_PATH, MODEL_PATH, load_classifier
from app.services.mood.vocabulary import load_vocabulary
from scripts.train_mood_model import build_pipeline, save
from tests.test_train_mood_model import SAMPLES


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A tiny model trained on the sample sentences, saved with its card."""
    texts = [t for ts in SAMPLES.values() for t in ts] * 4
    labels = [label for label, ts in SAMPLES.items() for _ in ts] * 4
    out_dir = tmp_path_factory.mktemp("model")
    save(build_pipeline(4.0).fit(texts, labels), {"note": "test model"}, out_dir, "test samples")
    return out_dir


def _paths(directory: Path) -> tuple[Path, Path]:
    return directory / "mood_model.joblib", directory / "mood_model_card.json"


def test_valid_model_loads_and_predicts(model_dir: Path) -> None:
    classifier = load_classifier(*_paths(model_dir))

    assert classifier is not None
    scores = classifier.predict("so happy right now")
    assert max(scores, key=lambda e: scores[e]) == "joy"
    assert sum(scores.values()) == pytest.approx(1.0)


def test_missing_model_falls_back(tmp_path: Path) -> None:
    assert load_classifier(*_paths(tmp_path)) is None


def test_tampered_model_is_refused(
    model_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    model, card = _paths(model_dir)
    bad_model, bad_card = _paths(tmp_path)
    bad_model.write_bytes(model.read_bytes() + b"tampered")
    bad_card.write_text(card.read_text(encoding="utf-8"), encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        assert load_classifier(bad_model, bad_card) is None
    assert "checksum" in caplog.text


def test_model_from_another_sklearn_version_is_refused(model_dir: Path, tmp_path: Path) -> None:
    model, card = _paths(model_dir)
    other_model, other_card = _paths(tmp_path)
    other_model.write_bytes(model.read_bytes())
    data = json.loads(card.read_text(encoding="utf-8"))
    data["sklearn_version"] = "0.0.1"
    other_card.write_text(json.dumps(data), encoding="utf-8")

    assert load_classifier(other_model, other_card) is None


def test_analyzer_uses_the_classifier_for_text(model_dir: Path) -> None:
    analyzer = MoodAnalyzer(load_vocabulary(), load_classifier(*_paths(model_dir)))

    profile = analyzer.analyze(MoodRequest(text="i feel so sad and empty"))

    assert profile.text_analysis == "classifier"
    assert profile.labels[0] == "sadness"
    assert profile.valence < 0.4


def test_analyzer_blends_chips_with_classified_text(model_dir: Path) -> None:
    analyzer = MoodAnalyzer(load_vocabulary(), load_classifier(*_paths(model_dir)))

    profile = analyzer.analyze(MoodRequest(chips=["calm"], text="so happy right now"))

    assert profile.labels[0] == "calm"
    assert "joy" in profile.labels


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="trained model not committed yet")
def test_committed_model_passes_its_integrity_check_and_reads_clear_moods() -> None:
    classifier = load_classifier()
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))

    assert classifier is not None, "committed model failed to load (checksum or version)"
    assert card["metrics"]["test_macro_f1"] >= 0.75
    scores = classifier.predict("i am so happy and grateful today")
    assert max(scores, key=lambda e: scores[e]) in {"joy", "love"}


class FakeClassifier:
    """Stands in for the trained model with fixed probabilities."""

    def __init__(self, probabilities: dict[str, float]) -> None:
        self.labels = list(probabilities)
        self._probabilities = probabilities

    def predict(self, text: str) -> dict[str, float]:
        return self._probabilities


UNSURE = {"joy": 0.31, "anger": 0.27, "sadness": 0.21, "fear": 0.1, "love": 0.06, "surprise": 0.05}
SURE = {"fear": 0.95, "joy": 0.01, "anger": 0.01, "sadness": 0.01, "love": 0.01, "surprise": 0.01}


def test_confident_classifier_reading_is_used() -> None:
    analyzer = MoodAnalyzer(load_vocabulary(), FakeClassifier(SURE))  # type: ignore[arg-type]

    profile = analyzer.analyze(MoodRequest(text="so nervous about the interview"))

    assert profile.text_analysis == "classifier"
    assert profile.labels == ["fear"]


def test_unsure_classifier_falls_back_to_mood_words() -> None:
    analyzer = MoodAnalyzer(load_vocabulary(), FakeClassifier(UNSURE))  # type: ignore[arg-type]

    profile = analyzer.analyze(MoodRequest(text="feeling drained tonight"))

    assert profile.text_analysis == "keywords"
    assert profile.labels == ["tired"]


def test_unsure_classifier_on_neutral_text_does_not_invent_a_mood() -> None:
    analyzer = MoodAnalyzer(load_vocabulary(), FakeClassifier(UNSURE))  # type: ignore[arg-type]

    profile = analyzer.analyze(
        MoodRequest(chips=["anxious", "low"], text="exams tomorrow, need to study")
    )

    assert profile.labels == ["anxious", "low"]  # no made-up "joy"
    assert profile.mode == "focus"

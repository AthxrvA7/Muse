"""Loads the trained free-text emotion classifier, safely.

A .joblib file is a pickle: loading it can run code. So we only load it if its
SHA-256 matches the model card written at training time (integrity check) and
it was trained with the same scikit-learn version we run (compatibility check).
If anything is off, Muse logs why and falls back to keyword matching.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import joblib
import sklearn

from app.services.mood.vocabulary import KNOWLEDGE_DIR

MODEL_PATH = KNOWLEDGE_DIR / "mood_model.joblib"
CARD_PATH = KNOWLEDGE_DIR / "mood_model_card.json"

logger = logging.getLogger(__name__)


class EmotionClassifier:
    """Wraps the scikit-learn pipeline: text in, probability per emotion out."""

    def __init__(self, pipeline: Any) -> None:
        self._pipeline = pipeline
        self.labels: list[str] = [str(label) for label in pipeline.classes_]

    def predict(self, text: str) -> dict[str, float]:
        probabilities = self._pipeline.predict_proba([text])[0]
        return {label: float(p) for label, p in zip(self.labels, probabilities, strict=True)}


def load_classifier(
    model_path: Path = MODEL_PATH, card_path: Path = CARD_PATH
) -> EmotionClassifier | None:
    if not model_path.exists() or not card_path.exists():
        logger.warning("Mood model not found; free text will use keyword matching")
        return None

    card = json.loads(card_path.read_text(encoding="utf-8"))
    actual = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if actual != card.get("sha256"):
        logger.error("Mood model checksum does not match its card; refusing to load it")
        return None
    if card.get("sklearn_version") != sklearn.__version__:
        logger.warning(
            "Mood model was trained with scikit-learn %s but %s is installed; not loading it",
            card.get("sklearn_version"),
            sklearn.__version__,
        )
        return None

    classifier = EmotionClassifier(joblib.load(model_path))  # safe: checksum verified above
    logger.info("Mood model loaded", extra={"labels": classifier.labels})
    return classifier

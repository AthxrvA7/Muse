"""Mood analysis: chips and/or free text -> MoodProfile.

1. Chips map straight to their valence/energy point; several chips are averaged.
2. Free text goes through the trained emotion classifier; each emotion's probability
   weights its point on the circumplex. If the model is unsure (or missing), the text
   is scanned for known mood words instead.
3. Chips and text are blended; chips weigh more because the user chose them on purpose.
4. Intent words ("study", "gym", "sleep") pick a playlist mode and nudge the energy.
5. A wellbeing check adds a support notice if the text suggests the person is in crisis.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.schemas.mood import Mode, MoodProfile, MoodRequest, Tempo
from app.services.mood.classifier import EmotionClassifier
from app.services.mood.vocabulary import MoodPoint, MoodVocabulary
from app.services.mood.wellbeing import WellbeingCheck

CHIP_WEIGHT = 0.7  # share of the final mood that comes from chips when text is also sent
CHIP_CONFIDENCE = 0.9
KEYWORD_CONFIDENCE = 0.6
LABEL_THRESHOLD = 0.3  # an emotion is named in the labels if the model gives it >= 30%
# Below this top probability the model is guessing (typical for neutral text like
# "need to study"), so Muse falls back to known mood words instead.
MIN_CLASSIFIER_CONFIDENCE = 0.5
NO_SIGNAL_CONFIDENCE = 0.2
NEUTRAL = MoodPoint(valence=0.5, energy=0.5)

# A word right after one of these is negated ("not happy") and is skipped
_NEGATION = r"(?<!\bnot )(?<!n't )(?<!\bnever )"


class UnknownChipError(ValueError):
    def __init__(self, unknown: list[str], allowed: list[str]) -> None:
        super().__init__(f"Unknown mood chip(s): {', '.join(unknown)}")
        self.unknown = unknown
        self.allowed = allowed


@dataclass(frozen=True)
class TextReading:
    """What Muse understood from the free text."""

    point: MoodPoint
    labels: list[str]
    confidence: float
    method: Literal["classifier", "keywords"]


def _pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(_NEGATION + r"\b" + re.escape(phrase) + r"\b")


def _average(points: Sequence[MoodPoint]) -> MoodPoint:
    return MoodPoint(
        valence=sum(p.valence for p in points) / len(points),
        energy=sum(p.energy for p in points) / len(points),
    )


def _blend(first: MoodPoint, second: MoodPoint, first_weight: float) -> MoodPoint:
    return MoodPoint(
        valence=first.valence * first_weight + second.valence * (1 - first_weight),
        energy=first.energy * first_weight + second.energy * (1 - first_weight),
    )


def tempo_for(energy: float) -> Tempo:
    if energy < 0.35:
        return "slow"
    if energy < 0.65:
        return "medium"
    return "fast"


class MoodAnalyzer:
    def __init__(
        self,
        vocabulary: MoodVocabulary,
        classifier: EmotionClassifier | None = None,
        wellbeing: WellbeingCheck | None = None,
    ) -> None:
        self._vocabulary = vocabulary
        self._classifier = classifier
        self._wellbeing = wellbeing
        self._mood_words = [
            (_pattern(word), chip_id)
            for chip_id, chip in vocabulary.chips.items()
            for word in [chip_id, *chip.synonyms]
        ]
        self._intent_words = [
            (_pattern(word), intent)
            for intent, words in vocabulary.intents.items()
            for word in words
        ]

    def analyze(self, request: MoodRequest) -> MoodProfile:
        unknown = [c for c in request.chips if c not in self._vocabulary.chips]
        if unknown:
            raise UnknownChipError(unknown, self._vocabulary.chip_ids)

        support = self._wellbeing.check(request.text) if self._wellbeing else None
        reading = self._read_text(request.text) if request.text else None
        point, labels, confidence = self._combine(request.chips, reading)

        intent = self._detect_intent(request.text) if request.text else None
        mode: Mode = request.mode or self._mode_for(intent)
        point = self._adjust_for(mode, intent, point)

        return MoodProfile(
            valence=round(point.valence, 2),
            energy=round(point.energy, 2),
            tempo=tempo_for(point.energy),
            mode=mode,
            labels=labels,
            confidence=round(confidence, 2),
            text_analysis=self._text_method(request.text, reading),
            support=support,
        )

    # ---- reading the input ----

    def _read_text(self, text: str) -> TextReading | None:
        if self._classifier:
            reading = self._classify(text, self._classifier)
            if reading.confidence >= MIN_CLASSIFIER_CONFIDENCE:
                return reading
        return self._match_keywords(text)

    @staticmethod
    def _text_method(
        text: str | None, reading: TextReading | None
    ) -> Literal["classifier", "keywords"] | None:
        if not text:
            return None
        # No reading means the keyword fallback ran and found no mood words
        return reading.method if reading else "keywords"

    def _classify(self, text: str, classifier: EmotionClassifier) -> TextReading:
        probabilities = {
            emotion: p
            for emotion, p in classifier.predict(text).items()
            if emotion in self._vocabulary.emotions
        }
        total = sum(probabilities.values())
        point = MoodPoint(
            valence=sum(self._vocabulary.emotions[e].valence * p for e, p in probabilities.items())
            / total,
            energy=sum(self._vocabulary.emotions[e].energy * p for e, p in probabilities.items())
            / total,
        )
        ranked = sorted(probabilities, key=lambda e: probabilities[e], reverse=True)
        labels = [e for e in ranked if probabilities[e] >= LABEL_THRESHOLD] or ranked[:1]
        return TextReading(point, labels, max(probabilities.values()) / total, "classifier")

    def _match_keywords(self, text: str) -> TextReading | None:
        lowered = text.lower()
        found = list(
            dict.fromkeys(
                chip_id for pattern, chip_id in self._mood_words if pattern.search(lowered)
            )
        )
        if not found:
            return None
        points = [self._vocabulary.chips[c] for c in found]
        return TextReading(_average(points), found, KEYWORD_CONFIDENCE, "keywords")

    def _combine(
        self, chips: list[str], reading: TextReading | None
    ) -> tuple[MoodPoint, list[str], float]:
        chip_point = _average([self._vocabulary.chips[c] for c in chips]) if chips else None

        if chip_point and reading:
            point = _blend(chip_point, reading.point, CHIP_WEIGHT)
            confidence = CHIP_CONFIDENCE * CHIP_WEIGHT + reading.confidence * (1 - CHIP_WEIGHT)
            return point, list(dict.fromkeys([*chips, *reading.labels])), confidence
        if chip_point:
            return chip_point, chips, CHIP_CONFIDENCE
        if reading:
            return reading.point, reading.labels, reading.confidence
        # Text with no recognisable mood in it
        return NEUTRAL, ["neutral"], NO_SIGNAL_CONFIDENCE

    def _detect_intent(self, text: str) -> str | None:
        lowered = text.lower()
        return next((i for pattern, i in self._intent_words if pattern.search(lowered)), None)

    # ---- modes ----

    @staticmethod
    def _mode_for(intent: str | None) -> Mode:
        if intent == "focus":
            return "focus"
        if intent == "energy":
            return "energy"
        if intent == "discovery":
            return "discovery"
        return "comfort"  # default, and for "sleep"

    @staticmethod
    def _adjust_for(mode: Mode, intent: str | None, point: MoodPoint) -> MoodPoint:
        energy = point.energy
        if mode == "focus":
            energy = min(max(energy, 0.30), 0.55)  # steady: not sleepy, not distracting
        elif mode == "energy":
            energy = max(energy, 0.75)
        if intent == "sleep":
            energy = min(energy, 0.20)
        return MoodPoint(valence=point.valence, energy=energy)

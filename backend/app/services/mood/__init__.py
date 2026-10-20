"""Mood engine: turns how the user feels into numbers Muse can rank music with."""

from functools import lru_cache

from app.services.mood.analyzer import MoodAnalyzer
from app.services.mood.classifier import load_classifier
from app.services.mood.vocabulary import get_vocabulary


@lru_cache
def get_mood_analyzer() -> MoodAnalyzer:
    """The analyzer, built once per process (FastAPI dependency)."""
    return MoodAnalyzer(get_vocabulary(), load_classifier())

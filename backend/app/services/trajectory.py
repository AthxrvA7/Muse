"""Mood trajectory: summarise how someone's moods moved over time.

Plain arithmetic on the logged moods, no model: averages, the most frequent mood words,
and whether the recent half of the period is lighter/heavier and more energetic/calmer
than the earlier half.
"""

from collections import Counter
from datetime import timedelta
from statistics import fmean

from app.schemas.moods import LabelCount, MoodAverage, MoodEntry, MoodTrajectory

MIN_POINTS_FOR_SHIFT = 4
SHIFT = 0.08  # a change smaller than this counts as "steady"
TOP_LABELS = 3


def _shift(points: list[MoodEntry], field: str) -> float:
    half = len(points) // 2
    older = fmean(getattr(p, field) for p in points[:half])
    newer = fmean(getattr(p, field) for p in points[-half:])
    return newer - older


def summarise(points: list[MoodEntry], days: int) -> MoodTrajectory:
    """``points`` oldest first."""
    if not points:
        return MoodTrajectory(
            days=days, points=[], average=None, top_labels=[], brightness=None, energy=None
        )
    counts = Counter(label for p in points for label in p.labels)
    top = [LabelCount(label=label, count=n) for label, n in counts.most_common(TOP_LABELS)]
    average = MoodAverage(
        valence=round(fmean(p.valence for p in points), 3),
        energy=round(fmean(p.energy for p in points), 3),
    )
    brightness = energy = None
    if len(points) >= MIN_POINTS_FOR_SHIFT:
        v, e = _shift(points, "valence"), _shift(points, "energy")
        brightness = "lighter" if v >= SHIFT else "heavier" if v <= -SHIFT else "steady"
        energy = "more energetic" if e >= SHIFT else "calmer" if e <= -SHIFT else "steady"
    return MoodTrajectory(
        days=days,
        points=points,
        average=average,
        top_labels=top,
        brightness=brightness,
        energy=energy,
    )


DAY_PARTS = ("morning", "afternoon", "evening", "night")


def day_part(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def by_day_part(points: list[MoodEntry], offset_minutes: int) -> dict[str, float]:
    """Average positivity per part of the day (local time), for parts with 2+ moods."""
    shift = timedelta(minutes=offset_minutes)
    groups: dict[str, list[float]] = {}
    for p in points:
        groups.setdefault(day_part((p.at + shift).hour), []).append(p.valence)
    return {part: fmean(v) for part in DAY_PARTS if len(v := groups.get(part, [])) >= 2}

"""Muse Rewind: a fun, shareable look back at your moods and music (the analysis part).

Plain, explainable rules on data Muse already holds; ``rewind_render`` draws the pages.
Nothing here is stored: the report is made on request and handed straight to the user.

- Personality: where the moods sat on average (positivity x energy), or "The
  Shapeshifter" when they were spread all over the map.
- Journey: the part of the map the period started in versus where it ended.
- Golden hour: the part of the day (in the user's own time zone) with the brightest moods.
- Taste x mood match: how close the feel of the user's genres is to their moods
  (1 - distance on the map, as a percentage).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import dist
from statistics import fmean

from app.db.models import PlaylistRecord
from app.schemas.feedback import FeedbackRecord, LearnedSummary
from app.schemas.moods import MoodEntry, MoodTrajectory
from app.schemas.preferences import MusicDNA
from app.services.learning import summarise as summarise_ratings
from app.services.trajectory import by_day_part, summarise

SHAPESHIFTER_SPREAD = 0.24  # average distance from the centre of the moods
SPANS = {7: "week", 30: "month", 90: "three months"}
MAX_DISTANCE = 2**0.5  # corner to corner of the mood map


@dataclass(frozen=True)
class Personality:
    name: str
    line: str


PERSONALITIES = {
    "shapeshifter": Personality(
        "The Shapeshifter", "Your moods moved all over the map, and your music moved with them."
    ),
    "bright": Personality("The Sunrise Chaser", "Bright, bold and always turning it up."),
    "calm": Personality("The Golden Hour Drifter", "Warm, easy and in no hurry at all."),
    "tense": Personality("The Midnight Engine", "Wired, restless and running on big feelings."),
    "low": Personality("The Rainy Window Poet", "Soft, slow and deep in your feelings."),
}


def quadrant(valence: float, energy: float) -> str:
    if energy >= 0.5:
        return "bright" if valence >= 0.5 else "tense"
    return "calm" if valence >= 0.5 else "low"


QUADRANT_WORDS = {
    "bright": "bright & lively",
    "calm": "calm & content",
    "tense": "tense & wired",
    "low": "low & slow",
}


def personality(points: list[MoodEntry]) -> Personality | None:
    if not points:
        return None
    v = fmean(p.valence for p in points)
    e = fmean(p.energy for p in points)
    spread = fmean(dist((p.valence, p.energy), (v, e)) for p in points)
    if len(points) >= 4 and spread >= SHAPESHIFTER_SPREAD:
        return PERSONALITIES["shapeshifter"]
    return PERSONALITIES[quadrant(v, e)]


def journey(points: list[MoodEntry]) -> str | None:
    """'You started the month tense & wired and ended it calm & content.'"""
    if len(points) < 2:
        return None
    first = quadrant(points[0].valence, points[0].energy)
    last = quadrant(points[-1].valence, points[-1].energy)
    if first == last:
        return f"You kept coming back to {QUADRANT_WORDS[first]}."
    return f"You started {QUADRANT_WORDS[first]} and ended {QUADRANT_WORDS[last]}."


def golden_hour(parts: dict[str, float]) -> str | None:
    if len(parts) < 2:
        return None
    best = max(parts, key=lambda part: parts[part])
    return "Nights" if best == "night" else f"{best.capitalize()}s"


def match(dna: MusicDNA | None, points: list[MoodEntry]) -> int | None:
    if not dna or not dna.mood_centre or not points:
        return None
    mood = (fmean(p.valence for p in points), fmean(p.energy for p in points))
    taste = (dna.mood_centre.valence, dna.mood_centre.energy)
    return round(100 * (1 - dist(mood, taste) / MAX_DISTANCE))


def match_line(score: int | None, dna: MusicDNA | None, points: list[MoodEntry]) -> str | None:
    if score is None or not dna or not dna.mood_centre:
        return None
    if score >= 85:
        return "Your music and your moods are in sync."
    mood = QUADRANT_WORDS[
        quadrant(fmean(p.valence for p in points), fmean(p.energy for p in points))
    ]
    return f"Your taste runs {dna.mood_centre.label}; your moods ran {mood}. Muse met you halfway."


def clean_name(name: str | None) -> str | None:
    """First name only, letters and simple punctuation (the PDF font is Latin only)."""
    if not name:
        return None
    first = name.split()[0] if name.split() else ""
    kept = "".join(c for c in first if c.isascii() and (c.isalnum() or c in "-'."))
    return kept[:20] or None


@dataclass
class Rewind:
    first_name: str | None
    days: int
    period: str
    generated: str
    moods_included: bool
    moods: list[MoodEntry] = field(default_factory=list)
    trajectory: MoodTrajectory | None = None
    top_mood: str | None = None
    top_mood_share: int | None = None
    personality: Personality | None = None
    journey: str | None = None
    day_parts: dict[str, float] = field(default_factory=dict)
    golden_hour: str | None = None
    dna: MusicDNA | None = None
    match: int | None = None
    match_line: str | None = None
    learned: LearnedSummary | None = None
    rated: int = 0
    playlists: list[PlaylistRecord] = field(default_factory=list)

    @property
    def span(self) -> str:
        return SPANS.get(self.days, f"{self.days} days")

    @property
    def title_owner(self) -> str:
        return f"{self.first_name}'s" if self.first_name else "Your"

    @property
    def pages(self) -> list[str]:
        """Which pages the report has, in order. Pages without data are left out."""
        has_taste = bool(self.dna and (self.dna.top_artists or self.dna.genres))
        wanted = [
            ("cover", True),
            ("mood_word", self.top_mood is not None),
            ("personality", self.personality is not None),
            ("journey", len(self.moods) >= 2),
            ("golden_hour", self.golden_hour is not None),
            ("sound", has_taste),
            ("match", self.match is not None),
            ("learned", bool(self.learned and (self.learned.likes or self.learned.dislikes))),
            ("playlists", bool(self.playlists)),
            ("outro", True),
        ]
        return [name for name, keep in wanted if keep]


def build_rewind(
    *,
    name: str | None,
    days: int,
    now: datetime,
    offset_minutes: int,
    moods: list[MoodEntry] | None,
    dna: MusicDNA | None,
    ratings: list[FeedbackRecord] | None,
    playlists: list[PlaylistRecord] | None,
) -> Rewind:
    """``None`` for a part means the user left it out of the report."""
    local = timezone(timedelta(minutes=offset_minutes))
    since = now - timedelta(days=days)
    start, end = since.astimezone(local), now.astimezone(local)
    period = f"{start.day} {start:%b} - {end.day} {end:%b %Y}"  # no %-d: Windows lacks it
    rewind = Rewind(
        first_name=clean_name(name),
        days=days,
        period=period,
        generated=f"{end.day} {end:%b %Y}",
        moods_included=moods is not None,
    )
    points = sorted((m for m in moods or [] if m.at >= since), key=lambda m: m.at)
    if points:
        rewind.moods = points
        rewind.trajectory = summarise(points, days)
        if rewind.trajectory.top_labels:
            top = rewind.trajectory.top_labels[0]
            rewind.top_mood = top.label
            rewind.top_mood_share = round(100 * top.count / len(points))
        rewind.personality = personality(points)
        rewind.journey = journey(points)
        rewind.day_parts = by_day_part(points, offset_minutes)
        rewind.golden_hour = golden_hour(rewind.day_parts)
    rewind.dna = dna
    rewind.match = match(dna, points)
    rewind.match_line = match_line(rewind.match, dna, points)
    if ratings is not None:
        rewind.learned = summarise_ratings(ratings)
        rewind.rated = sum(1 for r in ratings if r.updated_at >= since)
    if playlists is not None:
        rewind.playlists = sorted(
            (p for p in playlists if p.created_at >= since),
            key=lambda p: p.created_at,
            reverse=True,
        )
    return rewind

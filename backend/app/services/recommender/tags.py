"""Song moods from Last.fm listener tags.

Each tag that describes a feeling ("chill", "sad", "party") has a point on the
valence-energy map (``knowledge/mood_tags.json``); genre tags ("bollywood") use the
genre's point from ``genre_kb.json`` at half weight. A song's mood is the average of
its tag points, weighted by how strongly listeners use each tag.

Track tags are preferred; if a track has none, its artist's tags stand in (less certain).
"""

import asyncio
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Protocol

from pydantic import BaseModel

from app.clients.lastfm import Tag
from app.schemas.catalog import Track
from app.services.mood.vocabulary import KNOWLEDGE_DIR, MoodPoint
from app.services.recommender.knowledge import GenreKnowledge, match_genre

MIN_TAG_COUNT = 10  # ignore tags only a few listeners used
GENRE_TAG_WEIGHT = 0.5
MAX_SHOWN_WORDS = 3
LOOKUP_BUDGET_SECONDS = 6.0  # never let Last.fm hold a playlist up for long
MAX_TRACKS_TAGGED = 160


class TagKnowledge(BaseModel):
    version: int
    about: str
    tags: dict[str, MoodPoint]


@lru_cache
def get_tag_knowledge() -> TagKnowledge:
    path = KNOWLEDGE_DIR / "mood_tags.json"
    return TagKnowledge.model_validate_json(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class TagMood:
    point: MoodPoint
    certainty: float  # 0-1: how much to trust the point
    words: list[str]  # feeling tags to show the user, strongest first
    source: Literal["track", "artist"]


class TagSource(Protocol):
    async def track_tags(self, artist: str, track: str) -> list[Tag]: ...
    async def artist_tags(self, artist: str) -> list[Tag]: ...


def clean_title(name: str) -> str:
    """'Kasoor - Acoustic' -> 'Kasoor'; 'Song (feat. X)' -> 'Song' (what Last.fm knows)."""
    name = re.sub(r"\s[-–]\s.*$", "", name)
    name = re.sub(r"[(\[].*?[)\]]", "", name)
    return " ".join(name.split()) or name


def mood_from_tags(
    tags: list[Tag],
    tag_kb: TagKnowledge,
    genre_kb: GenreKnowledge,
    source: Literal["track", "artist"] = "track",
) -> TagMood | None:
    total = valence = energy = feeling_weight = 0.0
    words: list[str] = []
    for tag in tags:
        if tag.count < MIN_TAG_COUNT:
            continue
        point: MoodPoint | None = tag_kb.tags.get(tag.name)
        weight = float(tag.count)
        if point is not None:
            feeling_weight += weight
            words.append(tag.name)
        else:
            genre_id = match_genre(tag.name, genre_kb)
            if genre_id is None:
                continue
            point = genre_kb.genres[genre_id]
            weight *= GENRE_TAG_WEIGHT
        total += weight
        valence += weight * point.valence
        energy += weight * point.energy
    if total == 0:
        return None
    certainty = 0.9 if feeling_weight else 0.6  # feelings say more than genres
    if source == "artist":
        certainty -= 0.25  # the artist's usual feel, not this song's
    return TagMood(
        point=MoodPoint(valence=round(valence / total, 3), energy=round(energy / total, 3)),
        certainty=round(certainty, 2),
        words=words[:MAX_SHOWN_WORDS],
        source=source,
    )


async def tag_moods(
    lastfm: TagSource,
    tracks: list[Track],
    genre_kb: GenreKnowledge,
    budget: float = LOOKUP_BUDGET_SECONDS,
) -> dict[str, TagMood]:
    """Moods for as many tracks as Last.fm answers within the time budget (track id -> mood)."""
    tag_kb = get_tag_knowledge()
    artist_moods: dict[str, asyncio.Task[TagMood | None]] = {}

    async def artist_mood(artist: str) -> TagMood | None:
        return mood_from_tags(await lastfm.artist_tags(artist), tag_kb, genre_kb, "artist")

    async def one(track: Track) -> tuple[str, TagMood | None]:
        artist = track.artists[0].name if track.artists else ""
        if not artist:
            return track.id, None
        found = mood_from_tags(
            await lastfm.track_tags(artist, clean_title(track.name)), tag_kb, genre_kb
        )
        if found is None:  # fall back to the artist's tags, looked up once per artist
            if artist not in artist_moods:
                artist_moods[artist] = asyncio.ensure_future(artist_mood(artist))
            found = await artist_moods[artist]
        return track.id, found

    tasks = [asyncio.ensure_future(one(t)) for t in tracks[:MAX_TRACKS_TAGGED]]
    if not tasks:
        return {}
    done, pending = await asyncio.wait(tasks, timeout=budget)
    for task in pending | set(artist_moods.values()):
        task.cancel()
    moods: dict[str, TagMood] = {}
    for task in done:
        if not task.cancelled() and task.exception() is None:
            track_id, mood = task.result()
            if mood is not None:
                moods[track_id] = mood
    return moods

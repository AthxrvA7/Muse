"""Song moods, genres and languages from Last.fm listener tags.

Each tag that describes a feeling ("chill", "sad", "party") has a point on the
valence-energy map (``knowledge/mood_tags.json``); genre tags ("bollywood") use the
genre's point from ``genre_kb.json`` at half weight. A song's mood is the average of
its tag points, weighted by how strongly listeners use each tag.

Track tags are preferred; if a track has none, its artist's tags stand in (less certain).

The same tags (track and artist together) also say which genre a song belongs to and
what language it's sung in ("bollywood", "hindi", "k-pop"); the title's script helps too
(Devanagari means Hindi or Marathi, Hangul means Korean, ...).
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


# Tags that name a language (genre tags count too, through genre_kb.json)
LANGUAGE_TAGS = {
    "hindi": "hi", "bollywood": "hi", "indian": "hi", "hindustani": "hi",
    "punjabi": "pa", "bhangra": "pa", "urdu": "ur", "pakistani": "ur",
    "marathi": "mr", "tamil": "ta", "kollywood": "ta", "telugu": "te", "tollywood": "te",
    "malayalam": "ml", "bengali": "bn", "bangla": "bn",
    "korean": "ko", "k-pop": "ko", "kpop": "ko", "japanese": "ja", "j-pop": "ja", "jpop": "ja",
    "spanish": "es", "latin": "es", "reggaeton": "es", "english": "en",
}  # fmt: skip
SCRIPTS = (  # Unicode blocks -> language; checked on the title and artist names
    ("\u0900", "\u097f", "hi"), ("\u0a00", "\u0a7f", "pa"), ("\u0b80", "\u0bff", "ta"),
    ("\u0c00", "\u0c7f", "te"), ("\u0d00", "\u0d7f", "ml"), ("\u0980", "\u09ff", "bn"),
    ("\u0600", "\u06ff", "ur"), ("\uac00", "\ud7af", "ko"), ("\u3040", "\u30ff", "ja"),
)  # fmt: skip


def script_language(text: str) -> str | None:
    """The language a non-Latin script points to, if any letters use one."""
    for char in text:
        for first, last, language in SCRIPTS:
            if first <= char <= last:
                return language
    return None


def tag_genre(tags: list[Tag], genre_kb: GenreKnowledge) -> str | None:
    """The genre Muse knows that listeners use most for these tags."""
    votes: dict[str, float] = {}
    for tag in tags:
        if tag.count >= MIN_TAG_COUNT and (genre_id := match_genre(tag.name, genre_kb)):
            votes[genre_id] = votes.get(genre_id, 0.0) + tag.count
    return max(votes, key=lambda g: (votes[g], g)) if votes else None


def tag_language(tags: list[Tag], genre_kb: GenreKnowledge) -> str | None:
    """The language the tags point to most: language tags, then single-language genres."""
    votes: dict[str, float] = {}
    for tag in tags:
        if tag.count < MIN_TAG_COUNT:
            continue
        if tag.name in LANGUAGE_TAGS:
            language = LANGUAGE_TAGS[tag.name]
            votes[language] = votes.get(language, 0.0) + tag.count
        elif (genre_id := match_genre(tag.name, genre_kb)) and len(
            langs := genre_kb.genres[genre_id].langs
        ) == 1:
            votes[langs[0]] = votes.get(langs[0], 0.0) + tag.count * 0.6
    return max(votes, key=lambda code: (votes[code], code)) if votes else None


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


@dataclass(frozen=True)
class TrackProfile:
    """What Last.fm listeners (and the title's script) say about one song."""

    mood: TagMood | None
    genre: str | None  # genre id from genre_kb.json
    language: str | None  # ISO 639-1 code


async def profile_tracks(
    lastfm: TagSource,
    tracks: list[Track],
    genre_kb: GenreKnowledge,
    budget: float = LOOKUP_BUDGET_SECONDS,
) -> dict[str, TrackProfile]:
    """Profiles for as many tracks as Last.fm answers within the time budget (id -> profile)."""
    tag_kb = get_tag_knowledge()
    artist_tags: dict[str, asyncio.Task[list[Tag]]] = {}

    async def one(track: Track) -> tuple[str, TrackProfile]:
        artist = track.artists[0].name if track.artists else ""
        script = script_language(track.name + " " + " ".join(a.name for a in track.artists))
        if not artist:
            return track.id, TrackProfile(None, None, script)
        if artist not in artist_tags:  # looked up once per artist
            artist_tags[artist] = asyncio.ensure_future(lastfm.artist_tags(artist))
        own = await lastfm.track_tags(artist, clean_title(track.name))
        theirs = await artist_tags[artist]
        mood = mood_from_tags(own, tag_kb, genre_kb) or mood_from_tags(
            theirs, tag_kb, genre_kb, "artist"
        )
        both = own + theirs
        return track.id, TrackProfile(
            mood=mood,
            genre=tag_genre(own, genre_kb) or tag_genre(theirs, genre_kb),
            language=script or tag_language(both, genre_kb),
        )

    tasks = [asyncio.ensure_future(one(t)) for t in tracks[:MAX_TRACKS_TAGGED]]
    if not tasks:
        return {}
    done, pending = await asyncio.wait(tasks, timeout=budget)
    for task in pending | set(artist_tags.values()):
        task.cancel()
    profiles: dict[str, TrackProfile] = {}
    for task in done:
        if not task.cancelled() and task.exception() is None:
            track_id, profile = task.result()
            profiles[track_id] = profile
    return profiles


async def tag_moods(
    lastfm: TagSource,
    tracks: list[Track],
    genre_kb: GenreKnowledge,
    budget: float = LOOKUP_BUDGET_SECONDS,
) -> dict[str, TagMood]:
    """Just the moods (track id -> mood) for tracks Last.fm knows."""
    profiles = await profile_tracks(lastfm, tracks, genre_kb, budget)
    return {track_id: p.mood for track_id, p in profiles.items() if p.mood is not None}

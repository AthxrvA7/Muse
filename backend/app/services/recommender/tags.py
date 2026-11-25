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


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


# Words that give a romanised title away (most Hindi and Punjabi songs on Spotify are
# written in Latin letters, so the script alone can't tell)
HINDI_WORDS = _words(
    "mereya channa raataan lambiyan hawayein pehla nasha kalank khairiyat humsafar "
    "bekhayali shayad hawa kaun tujhpe chaiyya chhaiya mahiya sooraj chaand "
    "hai hain mein main tum tumhe tumse tera tere teri mera mere meri dil pyaar pyar "
    "ishq jaan zindagi kya nahi nahin yeh woh aankhein aankhon ankhon sajna sanam yaara "
    "raat baarish baarishein khwab duniya mohabbat tujhe mujhe tujhko hum humko kabhi "
    "jab bin tu kaise kyun dekha chal chalo aaja jaana jaane maahi mahi rabba khuda ek "
    "aur bhi kar karle hoon hoga tha thi phir saath pal lamhe dard yaad yaadein bewafa "
    "kesariya mann naina nain jiya piya sajan kahani galliyan shaam subah sapne bahut "
    "pehli dobara zara thoda dooriyan tujh mujh jahan jaha tujhse mujhse khamoshiyan "
    "judaa milke tujhme humnava hamari tumhari humari meherbaan ishqa raabta kabira "
    "ilahi agar teraa "
)
PUNJABI_WORDS = _words(
    "tenu mainu tainu jatt gabru kudi munda lagdi pind sardar nachna sohneya soniye "
    "mutiyaar wargi jehi vekh dekhda karda kardi rehnda rehndi chann pyaar ve "
)
ENGLISH_WORDS = _words(
    "the you your me my i i'm im love and of in to it is on for with we all be this that "
    "night heart baby don't dont can't cant feel like what when how never know girl time "
    "life go one just want need home light day dream away back up down out good bad "
    "little still again forever alone world without everything nothing somebody someone "
    "tonight yeah oh are was were been am she he they them her his our us do does did "
    "not no yes if so too more over under into from about after before every "
)


def title_language(name: str) -> str | None:
    """A guess from the words of a title: 'Tum Hi Ho' -> hi, 'Shape of You' -> en."""
    words = re.findall(r"[a-z']+", clean_title(name).lower())
    hindi = sum(w in HINDI_WORDS for w in words)
    punjabi = sum(w in PUNJABI_WORDS and w not in HINDI_WORDS for w in words)
    english = sum(w in ENGLISH_WORDS for w in words)
    if punjabi and punjabi + hindi > english:
        return "pa"
    if hindi > english:
        return "hi"
    if english > hindi:
        return "en"
    return None


def _language_votes(tags: list[Tag], genre_kb: GenreKnowledge) -> dict[str, float]:
    """Shares (summing to 1) of how much the tags point to each language."""
    votes: dict[str, float] = {}
    for tag in tags:
        if tag.count < MIN_TAG_COUNT:
            continue
        if tag.name in LANGUAGE_TAGS:
            language, weight = LANGUAGE_TAGS[tag.name], float(tag.count)
        elif (genre_id := match_genre(tag.name, genre_kb)) and len(
            langs := genre_kb.genres[genre_id].langs
        ) == 1:
            language, weight = langs[0], tag.count * 0.6
        else:
            continue
        votes[language] = votes.get(language, 0.0) + weight
    total = sum(votes.values())
    return {code: weight / total for code, weight in votes.items()} if total else {}


def _genre_votes(tags: list[Tag], genre_kb: GenreKnowledge) -> dict[str, float]:
    votes: dict[str, float] = {}
    for tag in tags:
        if tag.count >= MIN_TAG_COUNT and (genre_id := match_genre(tag.name, genre_kb)):
            votes[genre_id] = votes.get(genre_id, 0.0) + tag.count
    total = sum(votes.values())
    return {g: weight / total for g, weight in votes.items()} if total else {}


@dataclass(frozen=True)
class Hints:
    """What Muse already knows about a song without Last.fm (the search that found it)."""

    genre: str | None = None
    language: str | None = None


def decide_language(
    track: Track,
    own: list[Tag],
    artist: list[Tag],
    genre_kb: GenreKnowledge,
    hint: str | None = None,
) -> str | None:
    """Script decides outright; otherwise artist tags, song tags, title words and the
    search that found it vote. Needs a clear winner, or the language stays unknown."""
    names = track.name + " " + " ".join(a.name for a in track.artists)
    if script := script_language(names):
        return script
    votes: dict[str, float] = {}
    for weight, shares in (
        (3.0, _language_votes(artist, genre_kb)),
        (2.0, _language_votes(own, genre_kb)),
    ):
        for code, share in shares.items():
            votes[code] = votes.get(code, 0.0) + weight * share
    if from_title := title_language(track.name):
        votes[from_title] = votes.get(from_title, 0.0) + 2.0
    if hint:
        votes[hint] = votes.get(hint, 0.0) + 1.0
    if not votes:
        return None
    best = max(votes, key=lambda code: (votes[code], code))
    runner_up = max((v for code, v in votes.items() if code != best), default=0.0)
    return best if votes[best] >= 1.0 and votes[best] >= 1.5 * runner_up else None


def decide_genre(
    own: list[Tag], artist: list[Tag], genre_kb: GenreKnowledge, hint: str | None = None
) -> str | None:
    votes: dict[str, float] = {}
    for weight, shares in (
        (1.0, _genre_votes(artist, genre_kb)),
        (1.0, _genre_votes(own, genre_kb)),
    ):
        for genre_id, share in shares.items():
            votes[genre_id] = votes.get(genre_id, 0.0) + weight * share
    if hint:
        votes[hint] = votes.get(hint, 0.0) + 0.8
    return max(votes, key=lambda g: (votes[g], g)) if votes else None


@dataclass(frozen=True)
class TrackProfile:
    """What Last.fm listeners, the title and the search say about one song."""

    mood: TagMood | None
    genre: str | None  # genre id from genre_kb.json
    language: str | None  # ISO 639-1 code


MAX_ARTISTS_TAGGED = 50  # artist tags carry language and genre: looked up first
MAX_SONGS_TAGGED = 50  # song tags carry the finer mood: for the likeliest picks


async def profile_tracks(
    lastfm: TagSource,
    tracks: list[Track],
    genre_kb: GenreKnowledge,
    budget: float = LOOKUP_BUDGET_SECONDS,
    hints: dict[str, Hints] | None = None,
) -> dict[str, TrackProfile]:
    """A profile for every track (id -> profile), from whatever Last.fm answers in time.

    `tracks` should be ordered likeliest-pick first: song tags are only looked up for
    the first ones, artist tags for the first artists.
    """
    tag_kb = get_tag_knowledge()
    hints = hints or {}

    def main_artist(track: Track) -> str:
        return track.artists[0].name if track.artists else ""

    artists = list(dict.fromkeys(a for a in map(main_artist, tracks) if a))[:MAX_ARTISTS_TAGGED]
    artist_jobs = {a: asyncio.ensure_future(lastfm.artist_tags(a)) for a in artists}
    song_jobs = {
        t.id: asyncio.ensure_future(lastfm.track_tags(main_artist(t), clean_title(t.name)))
        for t in tracks[:MAX_SONGS_TAGGED]
        if main_artist(t)
    }
    jobs = [*artist_jobs.values(), *song_jobs.values()]
    if jobs:
        _, pending = await asyncio.wait(jobs, timeout=budget)
        for job in pending:
            job.cancel()

    def answer(job: asyncio.Task[list[Tag]] | None) -> list[Tag]:
        if job is None or not job.done() or job.cancelled() or job.exception() is not None:
            return []
        return job.result()

    profiles: dict[str, TrackProfile] = {}
    for track in tracks:
        own = answer(song_jobs.get(track.id))
        theirs = answer(artist_jobs.get(main_artist(track)))
        hint = hints.get(track.id, Hints())
        mood = mood_from_tags(own, tag_kb, genre_kb) or mood_from_tags(
            theirs, tag_kb, genre_kb, "artist"
        )
        profiles[track.id] = TrackProfile(
            mood=mood,
            genre=decide_genre(own, theirs, genre_kb, hint.genre),
            language=decide_language(track, own, theirs, genre_kb, hint.language),
        )
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

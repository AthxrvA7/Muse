"""Room mode: live, shared moods for a class or a group (kept in memory only).

A logged-in presenter opens a room and gets a short code. Anyone with the code can add
their mood by tapping up to three chips; only chips from Muse's fixed list are accepted,
so nothing anyone types reaches the big screen. Each phone has one vote and can change
it. Rooms expire after a few hours, and nothing about them is written to the database.
Against floods: new voters per minute are capped, and the host can lock the room or
reset its votes.

One process holds the rooms, which matches Muse's single instance (ADR-0001).
"""

import secrets
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from statistics import fmean

from app.schemas.mood import MoodRequest
from app.schemas.moods import LabelCount, MoodAverage, MoodEntry
from app.schemas.rooms import RoomPersonality, RoomPoint, RoomSummary
from app.services.mood import get_mood_analyzer
from app.services.mood.analyzer import MoodAnalyzer
from app.services.rewind import personality

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L: easy to read aloud
CODE_LENGTH = 4
ROOM_SECONDS = 4 * 60 * 60
MAX_ROOMS = 200
MAX_VOTERS = 500
NEW_VOTERS_PER_MINUTE = 150  # slows a script adding fake voters; a class joins well under it


class RoomNotFoundError(LookupError):
    pass


class RoomFullError(RuntimeError):
    pass


class TooManyRoomsError(RuntimeError):
    pass


class RoomLockedError(RuntimeError):
    pass


class NotHostError(PermissionError):
    pass


@dataclass
class Vote:
    valence: float
    energy: float
    labels: list[str]
    at: float


@dataclass
class Room:
    code: str
    host: str
    created: float
    votes: dict[str, Vote] = field(default_factory=dict)
    locked: bool = False
    joins: list[float] = field(default_factory=list)  # when new voters arrived (last minute)


class RoomStore:
    def __init__(self, analyzer: MoodAnalyzer, clock: Callable[[], float] = time.monotonic) -> None:
        self._analyzer = analyzer
        self._rooms: dict[str, Room] = {}
        self._now = clock

    def _expire(self) -> None:
        now = self._now()
        for code in [c for c, r in self._rooms.items() if now - r.created > ROOM_SECONDS]:
            del self._rooms[code]

    def create(self, host: str) -> str:
        self._expire()
        if len(self._rooms) >= MAX_ROOMS:  # refuse new rooms; never drop a live one
            raise TooManyRoomsError
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self._rooms:
                break
        self._rooms[code] = Room(code=code, host=host, created=self._now())
        return code

    def _room(self, code: str) -> Room:
        self._expire()
        room = self._rooms.get(code.upper())
        if room is None:
            raise RoomNotFoundError(code)
        return room

    def vote(self, code: str, voter: str, chips: list[str]) -> None:
        """Adds or changes this phone's mood. Raises UnknownChipError for unknown chips."""
        room = self._room(code)
        if voter not in room.votes:  # a new voter: the room must be open and not flooded
            if room.locked:
                raise RoomLockedError(code)
            now = self._now()
            room.joins = [t for t in room.joins if now - t < 60]
            if len(room.votes) >= MAX_VOTERS or len(room.joins) >= NEW_VOTERS_PER_MINUTE:
                raise RoomFullError(code)
            room.joins.append(now)
        profile = self._analyzer.analyze(MoodRequest(chips=chips, mode="comfort"))
        room.votes.pop(voter, None)  # a changed vote moves to the end (newest)
        room.votes[voter] = Vote(profile.valence, profile.energy, list(chips), self._now())

    def _hosted(self, code: str, host: str) -> Room:
        room = self._room(code)
        if room.host != host:
            raise NotHostError(code)
        return room

    def lock(self, code: str, host: str, locked: bool) -> None:
        """Locked: people already in can change their mood; nobody new can join."""
        self._hosted(code, host).locked = locked

    def reset(self, code: str, host: str) -> None:
        room = self._hosted(code, host)
        room.votes.clear()
        room.joins.clear()

    def summary(self, code: str) -> RoomSummary:
        room = self._room(code)
        votes = list(room.votes.values())  # oldest first (dicts keep insertion order)
        counts = Counter(label for v in votes for label in v.labels)
        average = (
            MoodAverage(
                valence=round(fmean(v.valence for v in votes), 3),
                energy=round(fmean(v.energy for v in votes), 3),
            )
            if votes
            else None
        )
        now = datetime.now(UTC)
        found = personality(
            [
                MoodEntry(
                    at=now, valence=v.valence, energy=v.energy, labels=v.labels, mode="comfort"
                )
                for v in votes
            ]
        )
        return RoomSummary(
            code=room.code,
            voters=len(votes),
            chips=[LabelCount(label=label, count=n) for label, n in counts.most_common()],
            points=[RoomPoint(valence=v.valence, energy=v.energy, labels=v.labels) for v in votes],
            average=average,
            personality=RoomPersonality(name=found.name, line=found.line) if found else None,
            locked=room.locked,
        )


@lru_cache(maxsize=1)
def get_room_store() -> RoomStore:
    """The one in-memory store for this process (FastAPI dependency)."""
    return RoomStore(get_mood_analyzer())

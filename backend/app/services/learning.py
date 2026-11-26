"""Learning from 👍/👎 ("Learn from me"): small, explainable nudges, never a black box.

From the user's ratings Muse works out:
- songs to leave out (👎) and songs to bring forward (👍; more so when the mood now is
  close to the mood they were liked in),
- how much the user likes or avoids each artist (👍 count minus 👎 count): an artist
  with two more 👎 than 👍 is left out; a liked artist is searched for even if they
  aren't in the Music DNA,
- a gentle lean towards genres the user likes.

Every nudge is small and capped, so the mood and the stated taste still lead.
"""

import math
from collections import Counter
from dataclasses import dataclass, field

from app.schemas.feedback import ArtistCount, FeedbackRecord, LearnedSummary
from app.schemas.mood import MoodProfile
from app.services.recommender.scoring import ScoredTrack

LIKED_SONG_BONUS = 0.1
SAME_MOOD_BONUS = 0.06  # extra when it was liked in a similar mood
SAME_MOOD_DISTANCE = 0.25
ARTIST_STEP = 0.04  # per net 👍 for an artist...
ARTIST_CAP = 0.12  # ...up to this
ARTIST_DISLIKE_STEP = 0.08
AVOID_ARTIST_AT = -2  # net 👍 - 👎 at which an artist is left out
GENRE_STEP = 0.02
GENRE_CAP = 0.06
LIKED_ARTISTS_TO_SEARCH = 2


@dataclass
class Learned:
    ratings: list[FeedbackRecord] = field(default_factory=list)
    liked_songs: dict[str, FeedbackRecord] = field(default_factory=dict)
    disliked_songs: set[str] = field(default_factory=set)
    artist_net: Counter[str] = field(default_factory=Counter)  # artist ID -> 👍 - 👎
    artist_names: dict[str, str] = field(default_factory=dict)
    genre_net: Counter[str] = field(default_factory=Counter)

    @property
    def empty(self) -> bool:
        return not self.ratings


def learn(ratings: list[FeedbackRecord]) -> Learned:
    learned = Learned(ratings=ratings)
    for rating in ratings:
        if rating.value > 0:
            learned.liked_songs[rating.track_id] = rating
        else:
            learned.disliked_songs.add(rating.track_id)
        for artist_id, name in zip(rating.artist_ids, rating.artist_names, strict=False):
            learned.artist_net[artist_id] += rating.value
            learned.artist_names.setdefault(artist_id, name)
        if rating.genre:
            learned.genre_net[rating.genre] += rating.value
    return learned


def liked_artists_to_search(learned: Learned, already: list[str]) -> list[str]:
    """Artist names the user has liked most that aren't searched already."""
    have = {name.lower() for name in already}
    liked = [
        learned.artist_names[a]
        for a, net in learned.artist_net.most_common()
        if net > 0 and learned.artist_names.get(a, "").lower() not in have
    ]
    return liked[:LIKED_ARTISTS_TO_SEARCH]


def apply_learning(
    scored: list[ScoredTrack], learned: Learned, mood: MoodProfile
) -> list[ScoredTrack]:
    """Leaves out 👎 songs and avoided artists; nudges the rest. Returns what's kept."""
    if learned.empty:
        return scored
    kept: list[ScoredTrack] = []
    for item in scored:
        track = item.candidate.track
        artist_ids = [a.id for a in track.artists]
        if track.id in learned.disliked_songs:
            continue
        if any(learned.artist_net[a] <= AVOID_ARTIST_AT for a in artist_ids):
            continue

        liked = learned.liked_songs.get(track.id)
        if liked is not None:
            item.score += LIKED_SONG_BONUS
            if liked.valence is not None and liked.energy is not None:
                apart = math.dist((liked.valence, liked.energy), (mood.valence, mood.energy))
                if apart <= SAME_MOOD_DISTANCE:
                    item.score += SAME_MOOD_BONUS
            item.learned = "liked"

        net = max((learned.artist_net[a] for a in artist_ids), default=0, key=abs)
        if net > 0:
            item.score += min(ARTIST_CAP, ARTIST_STEP * net)
            if item.learned is None:
                best = max(artist_ids, key=lambda a: learned.artist_net[a])
                item.learned = f"liked_artist:{learned.artist_names.get(best, '')}"
        elif net < 0:
            item.score -= ARTIST_DISLIKE_STEP * -net

        if item.genre and learned.genre_net[item.genre]:
            step = GENRE_STEP * learned.genre_net[item.genre]
            item.score += max(-GENRE_CAP, min(GENRE_CAP, step))

        item.score = round(max(0.0, min(1.0, item.score)), 3)
        kept.append(item)
    return kept


def summarise(ratings: list[FeedbackRecord]) -> "LearnedSummary":
    learned = learn(ratings)
    liked = [(a, n) for a, n in learned.artist_net.most_common() if n > 0][:8]
    avoided = sorted(((a, n) for a, n in learned.artist_net.items() if n < 0), key=lambda x: x[1])[
        :8
    ]
    return LearnedSummary(
        likes=sum(1 for r in ratings if r.value > 0),
        dislikes=sum(1 for r in ratings if r.value < 0),
        liked_artists=[ArtistCount(name=learned.artist_names[a], count=n) for a, n in liked],
        avoided_artists=[ArtistCount(name=learned.artist_names[a], count=-n) for a, n in avoided],
        ratings={r.track_id: r.value for r in ratings},
    )

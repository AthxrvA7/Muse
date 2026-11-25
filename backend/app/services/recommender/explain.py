"""Explanations: one plain sentence per track saying why Muse picked it.

Only factors that actually raised the track's score are mentioned (FR8):
the user's own top tracks, a favourite or similar artist, the favourite genre /
language / discovery genre that found it, and the mood match if the track's feel
(from Last.fm listener tags, or Muse's estimate) is close.
"""

from app.schemas.curate import Taste
from app.schemas.mood import MoodProfile
from app.services.recommender.knowledge import GenreKnowledge
from app.services.recommender.scoring import ScoredTrack

GOOD_MOOD_FIT = 0.75
EMOTION_WORDS = {
    "joy": "happy",
    "love": "loving",
    "surprise": "surprised",
    "sadness": "sad",
    "anger": "angry",
    "fear": "anxious",
}


def mood_phrase(mood: MoodProfile) -> str:
    """'tired, low' -> 'tired and low'; emotions become adjectives (fear -> anxious)."""
    words = [EMOTION_WORDS.get(label, label) for label in mood.labels if label != "neutral"]
    words = list(dict.fromkeys(words))[:2]
    return " and ".join(words) if words else "current"


def explain(item: ScoredTrack, mood: MoodProfile, taste: Taste, kb: GenreKnowledge) -> str:
    sources = {plan.reason: plan for plan in item.candidate.sources}
    parts: list[str] = []
    named: str | None = None  # genre already mentioned, so the mood clause doesn't repeat it

    if item.familiar_range == "short_term":
        parts.append("you've been playing it a lot lately")
    elif item.familiar_range:
        parts.append("it's one of your most-played songs")
    elif item.favourite_artist:
        parts.append(f"you like {item.favourite_artist}")
    elif item.similar_to:
        artist = item.candidate.track.artists[0].name if item.candidate.track.artists else "it"
        parts.append(f"{artist} is similar to {item.similar_to}, whom you like")
    elif item.taste_reason == "favourite_genre" and "favourite_genre" in sources:
        named = sources["favourite_genre"].value
        parts.append(f"it's {kb.genres[named].name}, one of your genres")
    elif item.taste_reason == "language" and "language" in sources:
        named = sources["language"].value
        genre = kb.genres[named]
        languages = [kb.languages[code] for code in genre.langs if code in taste.languages]
        parts.append(f"it's {genre.name} music in {languages[0] if languages else 'your language'}")
    elif item.taste_reason == "discovery" and "discovery" in sources:
        named = sources["discovery"].value
        parts.append(f"it's something new from {kb.genres[named].name}")

    if item.mood_fit >= GOOD_MOOD_FIT and item.tag_words:
        words = " and ".join(f"'{w}'" for w in item.tag_words[:2])
        parts.append(f"listeners tag it {words}, which fits your {mood_phrase(mood)} mood")
    elif item.mood_fit >= GOOD_MOOD_FIT and item.mood_source == "lastfm":
        parts.append(f"listeners' tags say it suits a {mood_phrase(mood)} mood")
    elif item.mood_fit >= GOOD_MOOD_FIT and item.mood_source:
        if item.mood_source in kb.genres:
            genres = [g for g in (item.mood_genres or [item.mood_source]) if g != named]
            names = list(dict.fromkeys(kb.genres[g].name for g in genres))[:2]
            feel = f"its {' and '.join(names)} feel" if names else "its feel"
        else:
            feel = f"its title has a {item.mood_source} feel"
        parts.append(f"{feel} fits your {mood_phrase(mood)} mood")

    if not parts:
        return "Included to round out the playlist with songs close to what you asked for."
    if item.bpm and item.tempo == mood.tempo:
        parts.append(f"at {item.bpm:.0f} BPM it keeps the {mood.tempo} pace you need")
    sentence = "Picked because " + ", and ".join(parts) + "."
    return sentence

"""Shared builders for recommender tests."""

from app.schemas.catalog import ArtistRef, Track
from app.schemas.mood import Mode, MoodProfile


def mood(
    valence: float, energy: float, mode: Mode = "comfort", labels: list[str] | None = None
) -> MoodProfile:
    return MoodProfile(
        valence=valence,
        energy=energy,
        tempo="medium",
        mode=mode,
        labels=labels or ["calm"],
        confidence=0.9,
        text_analysis=None,
    )


def track(
    track_id: str, artist: str = "Someone", name: str | None = None, **extra: object
) -> Track:
    data: dict[str, object] = {
        "id": track_id,
        "name": name or f"Song {track_id}",
        "artists": [ArtistRef(id=f"id-{artist}", name=artist)],
        "album": f"Album {track_id}",
        "release_year": 2020,
        "image_url": None,
        "spotify_url": f"https://open.spotify.com/track/{track_id}",
        "uri": f"spotify:track:{track_id}",
        "explicit": False,
        "duration_ms": 200_000,
    }
    data.update(extra)
    return Track.model_validate(data)

"""Saved taste profiles and the Music DNA summary (Classics: "Know your music")."""

from datetime import UTC, datetime

from app.db.models import Preferences
from app.schemas.curate import Taste
from app.schemas.preferences import (
    GenreInDNA,
    LanguageInDNA,
    MoodCentre,
    MusicDNA,
    PreferencesIn,
)
from app.services.curate import UnknownTasteError
from app.services.recommender.knowledge import GenreKnowledge


def check_known(preferences: PreferencesIn, kb: GenreKnowledge) -> None:
    """Genres and languages must be ones the recommender understands."""
    bad_genres = [g for g in preferences.genres if g not in kb.genres]
    bad_languages = [code for code in preferences.languages if code not in kb.languages]
    if bad_genres or bad_languages:
        raise UnknownTasteError(bad_genres, bad_languages)


def to_document(user_id: str, preferences: PreferencesIn) -> Preferences:
    return Preferences(user_id=user_id, updated_at=datetime.now(UTC), **preferences.model_dump())


def to_taste(preferences: Preferences) -> Taste:
    """The saved profile in the shape the recommender uses."""
    return Taste(
        artists=preferences.artists,
        genres=preferences.genres,
        languages=preferences.languages,
        exclude_artists=preferences.exclusions,
    )


def _centre_label(valence: float, energy: float) -> str:
    feel = "warm" if valence >= 0.5 else "melancholic"
    pace = "energetic" if energy >= 0.5 else "calm"
    return f"{pace} and {feel}"


def music_dna(preferences: Preferences | None, kb: GenreKnowledge) -> MusicDNA:
    if preferences is None:
        return MusicDNA(
            summary="No taste profile yet. Save one with PUT /api/v1/preferences.",
            top_artists=[],
            genres=[],
            languages=[],
            styles=[],
            mood_centre=None,
            reference_track_count=0,
            exclusion_count=0,
        )

    genres = [
        GenreInDNA(
            id=gid,
            name=kb.genres[gid].name,
            valence=kb.genres[gid].valence,
            energy=kb.genres[gid].energy,
        )
        for gid in preferences.genres
        if gid in kb.genres
    ]
    centre = None
    if genres:
        valence = round(sum(g.valence for g in genres) / len(genres), 3)
        energy = round(sum(g.energy for g in genres) / len(genres), 3)
        centre = MoodCentre(valence=valence, energy=energy, label=_centre_label(valence, energy))

    parts = [
        f"{len(preferences.artists)} favourite artist(s)",
        f"{len(genres)} genre(s)",
        f"{len(preferences.languages)} language(s)",
    ]
    summary = "Your stated taste: " + ", ".join(parts) + "."
    if centre:
        summary += f" On average your genres feel {centre.label}."

    return MusicDNA(
        summary=summary,
        top_artists=preferences.artists[:5],
        genres=genres,
        languages=[
            LanguageInDNA(code=code, name=kb.languages[code])
            for code in preferences.languages
            if code in kb.languages
        ],
        styles=preferences.styles,
        mood_centre=centre,
        reference_track_count=len(preferences.reference_tracks),
        exclusion_count=len(preferences.exclusions),
    )

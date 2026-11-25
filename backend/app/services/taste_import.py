"""Suggest a taste profile from the user's Spotify top artists ("Import from Spotify").

Muse still works only from what the user *states*: this returns a suggestion that the
website puts into the Music DNA form, and nothing is saved until the user reviews it and
presses Save. Muse reads the top-artist list once, on request, and never stores it,
analyses listening history, or uses it to train anything.

Spotify artist genres often come back empty in Development Mode, so the suggestion
always has artists, and genres/languages only when Spotify gives genres Muse knows.
"""

from collections import Counter
from typing import Protocol

import httpx2

from app.clients.spotify_user import TOP_ARTISTS_SCOPE, SpotifyUserClient, TopArtist
from app.db.models import User
from app.schemas.preferences import SpotifyTasteSuggestion
from app.services.recommender.knowledge import GenreKnowledge, match_genre

MAX_ARTISTS = 10  # same limit as the taste profile
MAX_GENRES = 5
MAX_LANGUAGES = 3


class MissingScopeError(Exception):
    """The user logged in before Muse asked for this permission: they must log in again."""


class TokenSource(Protocol):
    async def access_token(self, user_id: str) -> str: ...
    async def granted_scopes(self, user_id: str) -> set[str]: ...


def suggest_taste(artists: list[TopArtist], kb: GenreKnowledge) -> SpotifyTasteSuggestion:
    names = list(dict.fromkeys(a.name for a in artists))[:MAX_ARTISTS]

    genre_counts: Counter[str] = Counter()
    for artist in artists:
        matched = {g for g in (match_genre(s, kb) for s in artist.genres) if g}
        genre_counts.update(matched)  # one vote per artist per genre
    genres = [g for g, _ in genre_counts.most_common(MAX_GENRES)]

    language_counts: Counter[str] = Counter()
    for genre_id in genres:
        language_counts.update(kb.genres[genre_id].langs)
    languages = [code for code, _ in language_counts.most_common(MAX_LANGUAGES)]

    return SpotifyTasteSuggestion(artists=names, genres=genres, languages=languages)


class TasteImportService:
    def __init__(self, auth: TokenSource, http: httpx2.AsyncClient, kb: GenreKnowledge) -> None:
        self._auth = auth
        self._http = http
        self._kb = kb

    async def suggest(self, user: User) -> SpotifyTasteSuggestion:
        if TOP_ARTISTS_SCOPE not in await self._auth.granted_scopes(user.id):
            raise MissingScopeError("Log in with Spotify again to allow reading top artists")
        token = await self._auth.access_token(user.id)
        artists = await SpotifyUserClient(self._http, token).top_artists(limit=MAX_ARTISTS)
        return suggest_taste(artists, self._kb)

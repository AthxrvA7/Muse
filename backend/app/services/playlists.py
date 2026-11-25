"""Creating the curated playlist in the user's own Spotify account (FR9)."""

from datetime import UTC, datetime
from typing import Protocol

import httpx2

from app.clients.spotify_user import SpotifyUserClient
from app.db.models import PlaylistRecord, User
from app.db.repositories.playlists import PlaylistRepository
from app.schemas.playlists import ExportRequest
from app.services.auth import AuthService


class TokenSource(Protocol):
    async def access_token(self, user_id: str) -> str: ...


class PlaylistService:
    def __init__(
        self, auth: AuthService | TokenSource, http: httpx2.AsyncClient, repo: PlaylistRepository
    ) -> None:
        self._auth = auth
        self._http = http
        self._repo = repo

    async def export(self, user: User, request: ExportRequest) -> PlaylistRecord:
        token = await self._auth.access_token(user.id)  # refreshed if about to expire
        spotify = SpotifyUserClient(self._http, token)
        playlist = await spotify.create_playlist(request.name, request.description)
        await spotify.add_tracks(playlist.id, request.track_ids)
        return await self._repo.add(
            PlaylistRecord(
                user_id=user.id,
                spotify_playlist_id=playlist.id,
                url=playlist.url,
                name=request.name,
                track_count=len(request.track_ids),
                created_at=datetime.now(UTC),
            )
        )

    async def history(self, user: User) -> list[PlaylistRecord]:
        return await self._repo.list_for_user(user.id)

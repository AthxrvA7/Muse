"""Creating the curated playlist in the user's own Spotify account (FR9)."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Literal, Protocol

import httpx2

from app.clients.spotify_user import COVER_SCOPE, SpotifyUserClient
from app.db.models import PlaylistRecord, User
from app.db.repositories.playlists import PlaylistRepository
from app.schemas.playlists import ExportRequest
from app.services.auth import AuthService
from app.services.cover import make_cover

logger = logging.getLogger(__name__)


class TokenSource(Protocol):
    async def access_token(self, user_id: str) -> str: ...
    async def granted_scopes(self, user_id: str) -> set[str]: ...


CoverResult = Literal["added", "needs_login", "failed", "none"]


class PlaylistService:
    def __init__(
        self, auth: AuthService | TokenSource, http: httpx2.AsyncClient, repo: PlaylistRepository
    ) -> None:
        self._auth = auth
        self._http = http
        self._repo = repo

    async def export(
        self, user: User, request: ExportRequest
    ) -> tuple[PlaylistRecord, CoverResult]:
        token = await self._auth.access_token(user.id)  # refreshed if about to expire
        spotify = SpotifyUserClient(self._http, token)
        playlist = await spotify.create_playlist(request.name, request.description)
        await spotify.add_tracks(playlist.id, request.track_ids)
        cover = await self._add_cover(user, spotify, playlist.id, request)
        record = await self._repo.add(
            PlaylistRecord(
                user_id=user.id,
                spotify_playlist_id=playlist.id,
                url=playlist.url,
                name=request.name,
                track_count=len(request.track_ids),
                created_at=datetime.now(UTC),
            )
        )
        return record, cover

    async def _add_cover(
        self, user: User, spotify: SpotifyUserClient, playlist_id: str, request: ExportRequest
    ) -> CoverResult:
        """The cover is a bonus: any problem leaves the (already saved) playlist as it is."""
        if request.cover is None:
            return "none"
        try:
            if COVER_SCOPE not in await self._auth.granted_scopes(user.id):
                return "needs_login"  # logged in before Muse asked for this permission
            jpeg = await asyncio.to_thread(
                make_cover,
                request.cover.valence,
                request.cover.energy,
                request.cover.title,
                request.cover.words,
            )
            await spotify.upload_cover(playlist_id, jpeg)
            return "added"
        except Exception:
            logger.warning("Could not add the cover", exc_info=True)
            return "failed"

    async def history(self, user: User) -> list[PlaylistRecord]:
        return await self._repo.list_for_user(user.id)

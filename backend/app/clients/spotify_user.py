"""Spotify calls made on behalf of a logged-in user (Authorization Code flow).

The app-only client (``spotify.py``) can search the catalogue. Creating a playlist in
someone's account needs that person's permission, so it uses *their* access token,
obtained when they log in with Spotify. Tokens are never logged or sent to the browser.
"""

import asyncio
import base64
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx2

from app.clients.spotify import (
    API_URL,
    MAX_RETRY_AFTER,
    TOKEN_URL,
    SpotifyAuthError,
    SpotifyError,
    SpotifyRateLimitError,
    SpotifyUnavailableError,
    _parse_track,
)
from app.schemas.catalog import Track

logger = logging.getLogger(__name__)

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
# The minimum Muse needs: create playlists, read the user's Spotify ID and name, and
# read their top artists and tracks (to suggest a taste profile, and to start playlists
# from songs the user already plays; never stored)
SCOPES = (
    "playlist-modify-private",
    "playlist-modify-public",
    "user-read-private",
    "user-top-read",
    "ugc-image-upload",  # only to put Muse's cover art on a playlist Muse just created
)
COVER_SCOPE = "ugc-image-upload"
TOP_ARTISTS_SCOPE = "user-top-read"
MAX_ITEMS_PER_REQUEST = 100  # Spotify's limit for adding items to a playlist

# Safety guard: the ONLY calls Muse may make with a user's token. Muse never deletes,
# edits, reorders or reads anyone's existing playlists or library. Any other request is
# refused before it leaves the server (tested in test_spotify_user.py).
ALLOWED_USER_CALLS = (
    ("GET", re.compile(r"^/me$")),  # read the user's Spotify ID and display name
    ("GET", re.compile(r"^/me/top/artists$")),  # read-only: suggest a taste profile
    ("GET", re.compile(r"^/me/top/tracks$")),  # read-only: songs the user plays most
    ("PUT", re.compile(r"^/playlists/[A-Za-z0-9]+/images$")),  # cover art, own new playlist only
    ("POST", re.compile(r"^/me/playlists$")),  # create a NEW playlist
    ("POST", re.compile(r"^/playlists/[A-Za-z0-9]+/items$")),  # add tracks to it
)


class ForbiddenCallError(RuntimeError):
    """Code tried to make a Spotify call outside ALLOWED_USER_CALLS (a programming error)."""


class SpotifyLoginError(SpotifyError):
    """The login code or refresh token was rejected (expired, reused or revoked)."""


class SpotifyForbiddenError(SpotifyError):
    """Spotify refused the action, e.g. the account isn't on the app's Development Mode list."""


@dataclass(frozen=True)
class UserTokens:
    access_token: str
    refresh_token: str
    expires_at: float  # Unix time (seconds) when the access token stops working
    scope: str

    def expires_soon(self, margin: float = 60) -> bool:
        return time.time() >= self.expires_at - margin


@dataclass(frozen=True)
class SpotifyProfile:
    id: str
    display_name: str | None


@dataclass(frozen=True)
class TopArtist:
    name: str
    genres: list[str]  # often empty in Development Mode


@dataclass(frozen=True)
class CreatedPlaylist:
    id: str
    url: str


def authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    """The Spotify consent page the browser is sent to."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": " ".join(SCOPES),
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


class SpotifyUserAuth:
    """Exchanges a login code for tokens, and refreshes expired access tokens."""

    def __init__(self, http: httpx2.AsyncClient, client_id: str, client_secret: str) -> None:
        self._http = http
        self._auth = httpx2.BasicAuth(client_id, client_secret)

    async def exchange_code(self, code: str, redirect_uri: str) -> UserTokens:
        body = await self._token_request(
            {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
        )
        return _tokens(body, previous_refresh_token=None)

    async def refresh(self, refresh_token: str) -> UserTokens:
        body = await self._token_request(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )
        # Spotify may or may not send a new refresh token; keep the old one if not
        return _tokens(body, previous_refresh_token=refresh_token)

    async def _token_request(self, data: dict[str, str]) -> dict[str, Any]:
        try:
            response = await self._http.post(TOKEN_URL, data=data, auth=self._auth)
        except httpx2.TransportError as error:
            raise SpotifyUnavailableError("Could not reach Spotify accounts service") from error
        if response.status_code == 200:
            result: dict[str, Any] = response.json()
            return result
        if response.status_code == 400:
            # invalid_grant: code expired/reused, or refresh token revoked
            raise SpotifyLoginError("Spotify rejected the login; please log in again")
        if response.status_code == 401:
            raise SpotifyAuthError("Spotify rejected Muse's client credentials")
        raise SpotifyUnavailableError(f"Spotify token endpoint returned {response.status_code}")


def _tokens(body: dict[str, Any], previous_refresh_token: str | None) -> UserTokens:
    refresh_token = body.get("refresh_token") or previous_refresh_token
    if not refresh_token:
        raise SpotifyLoginError("Spotify did not return a refresh token")
    return UserTokens(
        access_token=body["access_token"],
        refresh_token=refresh_token,
        expires_at=time.time() + int(body.get("expires_in", 3600)),
        scope=body.get("scope", ""),
    )


class SpotifyUserClient:
    """API calls with one user's access token."""

    def __init__(self, http: httpx2.AsyncClient, access_token: str) -> None:
        self._http = http
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._created: set[str] = set()  # playlists this client created (the only ones it may fill)

    async def me(self) -> SpotifyProfile:
        body = await self._request("GET", "/me")
        return SpotifyProfile(id=body["id"], display_name=body.get("display_name"))

    async def top_artists(
        self, limit: int = 10, time_range: str = "medium_term"
    ) -> list[TopArtist]:
        """The user's most-played artists (about the last 6 months). Read-only."""
        body = await self._request(
            "GET", "/me/top/artists", params={"limit": limit, "time_range": time_range}
        )
        return [
            TopArtist(name=item["name"], genres=list(item.get("genres") or []))
            for item in body.get("items", [])
            if item.get("name")
        ]

    async def top_tracks(self, time_range: str = "short_term", limit: int = 50) -> list[Track]:
        """The user's most-played tracks: short_term ~4 weeks, medium_term ~6 months."""
        body = await self._request(
            "GET", "/me/top/tracks", params={"limit": limit, "time_range": time_range}
        )
        tracks = (_parse_track(item) for item in body.get("items", []) if item)
        return [track for track in tracks if track is not None]

    async def create_playlist(self, name: str, description: str) -> CreatedPlaylist:
        """Creates a NEW private playlist in the user's account (Feb-2026 endpoint)."""
        body = await self._request(
            "POST", "/me/playlists", {"name": name, "description": description, "public": False}
        )
        url = (
            body.get("external_urls", {}).get("spotify")
            or f"https://open.spotify.com/playlist/{body['id']}"
        )
        self._created.add(body["id"])
        return CreatedPlaylist(id=body["id"], url=url)

    async def add_tracks(self, playlist_id: str, track_ids: list[str]) -> None:
        """Adds tracks, but only to a playlist this client has just created."""
        if playlist_id not in self._created:
            raise ForbiddenCallError("Muse only adds tracks to playlists it has just created")
        uris = [f"spotify:track:{track_id}" for track_id in track_ids]
        for start in range(0, len(uris), MAX_ITEMS_PER_REQUEST):
            await self._request(
                "POST",
                f"/playlists/{playlist_id}/items",
                {"uris": uris[start : start + MAX_ITEMS_PER_REQUEST]},
            )

    async def upload_cover(self, playlist_id: str, jpeg: bytes) -> None:
        """Puts a cover image on a playlist this client has just created (base64 JPEG)."""
        if playlist_id not in self._created:
            raise ForbiddenCallError("Muse only adds covers to playlists it has just created")
        await self._request(
            "PUT",
            f"/playlists/{playlist_id}/images",
            content=base64.b64encode(jpeg),
            content_type="image/jpeg",
        )

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        if not any(method == m and pattern.match(path) for m, pattern in ALLOWED_USER_CALLS):
            raise ForbiddenCallError(f"Muse may not call {method} {path} with a user's token")
        waited = retried = False
        while True:
            try:
                headers = self._headers
                if content_type:
                    headers = {**headers, "Content-Type": content_type}
                response = await self._http.request(
                    method,
                    f"{API_URL}{path}",
                    json=json,
                    params=params,
                    content=content,
                    headers=headers,
                )
            except httpx2.TransportError as error:
                if retried or method != "GET":  # never repeat a write that may have happened
                    raise SpotifyUnavailableError("Spotify did not respond") from error
                retried = True
                continue

            status = response.status_code
            if status in (200, 201, 202):  # 202: Spotify accepted an image upload
                result: dict[str, Any] = response.json() if response.content else {}
                return result
            if status == 401:
                raise SpotifyLoginError("The Spotify login has expired; please log in again")
            if status == 403:
                raise SpotifyForbiddenError("Spotify refused this action for this account")
            if status == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                if waited or retry_after > MAX_RETRY_AFTER:
                    raise SpotifyRateLimitError(retry_after)
                waited = True
                await asyncio.sleep(retry_after)
                continue
            if status >= 500 and not retried and method == "GET":
                retried = True
                continue
            logger.warning(
                "Spotify user request failed", extra={"path": path, "status_code": status}
            )
            if status >= 500:
                raise SpotifyUnavailableError(f"Spotify returned {status}")
            raise SpotifyError(f"Spotify returned {status}")

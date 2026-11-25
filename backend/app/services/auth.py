"""Logging in with Spotify, server-side sessions, and access to a user's Spotify token.

How a login works (ARCHITECTURE §4.2):
1. ``start_login`` stores a random ``state`` and returns Spotify's consent-page URL.
2. Spotify sends the browser back with ``code`` and ``state``. ``finish_login`` accepts
   it only if that state was issued by Muse in the last 10 minutes and never used
   (defence against login CSRF), exchanges the code for tokens, reads the profile,
   saves the user, stores the tokens encrypted, and starts a session.
3. The browser gets only a random session ID in an httpOnly cookie. Muse stores just its
   SHA-256 hash, so logout works instantly and a database leak reveals no usable IDs.
"""

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.clients.spotify_user import (
    SpotifyProfile,
    SpotifyUserAuth,
    UserTokens,
    authorize_url,
)
from app.core.crypto import TokenCipher, TokenDecryptError
from app.db.indexes import OAUTH_STATE_SECONDS
from app.db.models import User
from app.db.repositories.oauth_states import OAuthStateRepository
from app.db.repositories.sessions import SessionRepository
from app.db.repositories.users import UserRepository

SESSION_COOKIE = "muse_session"


class LoginStateError(Exception):
    """The callback's state is unknown, already used, or too old."""


class NotLoggedInError(Exception):
    """No valid Spotify tokens are stored for this user; they need to log in again."""


class ProfileReader(Protocol):
    async def me(self) -> SpotifyProfile: ...


def hash_session_id(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        states: OAuthStateRepository,
        cipher: TokenCipher,
        spotify_auth: SpotifyUserAuth,
        profile_reader: Callable[[str], ProfileReader],
        client_id: str,
        redirect_uri: str,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.states = states
        self.cipher = cipher
        self.spotify_auth = spotify_auth
        self.profile_reader = profile_reader  # access token -> client that can read /me
        self.client_id = client_id
        self.redirect_uri = redirect_uri

    # ---------- login ----------

    async def start_login(self) -> str:
        state = secrets.token_urlsafe(32)
        await self.states.create(state)
        return authorize_url(self.client_id, self.redirect_uri, state)

    async def finish_login(self, code: str, state: str) -> tuple[str, User]:
        """Returns (new session ID for the cookie, the user)."""
        created_at = await self.states.consume(state)  # single use: deleted here
        max_age = timedelta(seconds=OAUTH_STATE_SECONDS)
        if created_at is None or datetime.now(UTC) - created_at > max_age:
            raise LoginStateError("This login link is invalid or expired; please start again")

        tokens = await self.spotify_auth.exchange_code(code, self.redirect_uri)
        profile = await self.profile_reader(tokens.access_token).me()
        user = await self.users.upsert_on_login(profile.id, profile.display_name)
        await self._save_tokens(user.id, tokens)

        session_id = secrets.token_urlsafe(32)  # a fresh ID on every login (no fixation)
        await self.sessions.create(hash_session_id(session_id), user.id)
        return session_id, user

    # ---------- sessions ----------

    async def user_for_session(self, session_id: str | None) -> User | None:
        if not session_id:
            return None
        id_hash = hash_session_id(session_id)
        session = await self.sessions.get(id_hash)
        if session is None:
            return None
        user = await self.users.get(session.user_id)
        if user is None:  # account deleted: the session must not outlive it
            await self.sessions.delete(id_hash)
            return None
        await self.sessions.touch(id_hash)  # restarts the 7-day idle timer
        return user

    async def logout(self, session_id: str | None) -> None:
        if session_id:
            await self.sessions.delete(hash_session_id(session_id))

    # ---------- the user's Spotify token ----------

    async def access_token(self, user_id: str) -> str:
        """A working access token for this user, refreshed first if it's about to expire."""
        stored = await self.users.get_tokens(user_id)
        if not stored:
            raise NotLoggedInError("No Spotify login stored; please log in again")
        try:
            tokens = UserTokens(
                access_token=self.cipher.decrypt(stored["access_token"]),
                refresh_token=self.cipher.decrypt(stored["refresh_token"]),
                expires_at=float(stored["expires_at"]),
                scope=stored.get("scope", ""),
            )
        except TokenDecryptError as error:  # e.g. the encryption key was rotated
            raise NotLoggedInError(
                "Stored Spotify login is unreadable; please log in again"
            ) from error

        if tokens.expires_soon():
            tokens = await self.spotify_auth.refresh(tokens.refresh_token)
            await self._save_tokens(user_id, tokens)
        return tokens.access_token

    async def granted_scopes(self, user_id: str) -> set[str]:
        """The Spotify permissions this user granted at their last login."""
        stored = await self.users.get_tokens(user_id)
        if not stored:
            raise NotLoggedInError("No Spotify login stored; please log in again")
        return set(str(stored.get("scope", "")).split())

    async def _save_tokens(self, user_id: str, tokens: UserTokens) -> None:
        await self.users.save_tokens(
            user_id,
            {
                "access_token": self.cipher.encrypt(tokens.access_token),
                "refresh_token": self.cipher.encrypt(tokens.refresh_token),
                "expires_at": tokens.expires_at,
                "scope": tokens.scope,
            },
        )

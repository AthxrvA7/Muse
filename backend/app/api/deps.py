"""Shared FastAPI dependencies: the auth service and the logged-in user."""

from collections.abc import AsyncIterator
from typing import Annotated

import httpx2
from fastapi import Depends, HTTPException, Request, status

from app.clients.spotify_user import SpotifyUserAuth, SpotifyUserClient
from app.core.crypto import TokenCipher
from app.db.models import User
from app.db.repositories.oauth_states import OAuthStateRepository
from app.db.repositories.playlists import PlaylistRepository
from app.db.repositories.preferences import PreferencesRepository
from app.db.repositories.sessions import SessionRepository
from app.db.repositories.users import UserRepository
from app.schemas.curate import Taste
from app.services.auth import SESSION_COOKIE, AuthService
from app.services.playlists import PlaylistService
from app.services.preferences import to_taste
from app.services.privacy import PrivacyService

NOT_LOGGED_IN = {"message": "Log in with Spotify first: open /api/v1/auth/login"}


async def get_http(request: Request) -> AsyncIterator[httpx2.AsyncClient]:
    """One HTTP client per request for user-token calls to Spotify."""
    async with httpx2.AsyncClient(
        timeout=request.app.state.settings.spotify_timeout_seconds
    ) as http:
        yield http


def get_auth_service(
    request: Request, http: Annotated[httpx2.AsyncClient, Depends(get_http)]
) -> AuthService:
    settings = request.app.state.settings
    database = request.app.state.db
    if not settings.login_configured or database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Login isn't set up on this server (needs Spotify credentials, "
                "MONGODB_URI and TOKEN_ENCRYPTION_KEY)"
            },
        )
    return AuthService(
        users=UserRepository(database),
        sessions=SessionRepository(database),
        states=OAuthStateRepository(database),
        cipher=TokenCipher(settings.token_encryption_key.get_secret_value()),
        spotify_auth=SpotifyUserAuth(
            http, settings.spotify_client_id, settings.spotify_client_secret.get_secret_value()
        ),
        profile_reader=lambda token: SpotifyUserClient(http, token),
        client_id=settings.spotify_client_id,
        redirect_uri=settings.spotify_redirect_uri,
    )


async def current_user(
    request: Request, auth: Annotated[AuthService, Depends(get_auth_service)]
) -> User:
    """The logged-in user, or 401. Use as a dependency on every personal endpoint."""
    user = await auth.user_for_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=NOT_LOGGED_IN)
    return user


async def optional_user(
    request: Request, http: Annotated[httpx2.AsyncClient, Depends(get_http)]
) -> User | None:
    """The logged-in user if there is one; None otherwise (never an error).

    For endpoints that work for everyone but do more when you're logged in (curate).
    """
    session_id = request.cookies.get(SESSION_COOKIE)
    settings = request.app.state.settings
    if not session_id or not settings.login_configured or request.app.state.db is None:
        return None
    return await get_auth_service(request, http).user_for_session(session_id)


def get_preferences_repository(request: Request) -> PreferencesRepository:
    database = request.app.state.db
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Saving preferences needs the database (MONGODB_URI)"},
        )
    return PreferencesRepository(database)


async def saved_taste(
    request: Request, user: Annotated[User | None, Depends(optional_user)]
) -> Taste | None:
    """The logged-in user's saved taste profile, if they have one."""
    if user is None or request.app.state.db is None:
        return None
    saved = await PreferencesRepository(request.app.state.db).get(user.id)
    return to_taste(saved) if saved else None


def get_playlist_service(
    request: Request,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    http: Annotated[httpx2.AsyncClient, Depends(get_http)],
) -> PlaylistService:
    return PlaylistService(auth, http, PlaylistRepository(request.app.state.db))


def get_privacy_service(request: Request) -> PrivacyService:
    database = request.app.state.db
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "This needs the database (MONGODB_URI)"},
        )
    return PrivacyService(
        UserRepository(database),
        SessionRepository(database),
        PreferencesRepository(database),
        PlaylistRepository(database),
    )


CurrentUser = Annotated[User, Depends(current_user)]
SavedTaste = Annotated[Taste | None, Depends(saved_taste)]
OptionalUser = Annotated[User | None, Depends(optional_user)]
PreferencesRepo = Annotated[PreferencesRepository, Depends(get_preferences_repository)]
Auth = Annotated[AuthService, Depends(get_auth_service)]

"""Shared FastAPI dependencies: the auth service and the logged-in user."""

from collections.abc import AsyncIterator
from typing import Annotated

import httpx2
from fastapi import Depends, HTTPException, Request, status

from app.clients.spotify_user import SpotifyUserAuth, SpotifyUserClient
from app.core.crypto import TokenCipher
from app.db.models import User
from app.db.repositories.oauth_states import OAuthStateRepository
from app.db.repositories.sessions import SessionRepository
from app.db.repositories.users import UserRepository
from app.services.auth import SESSION_COOKIE, AuthService

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


CurrentUser = Annotated[User, Depends(current_user)]
Auth = Annotated[AuthService, Depends(get_auth_service)]

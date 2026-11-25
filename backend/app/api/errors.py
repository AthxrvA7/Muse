"""Turning service errors into clear HTTP errors (no internal details leak)."""

from fastapi import HTTPException, status

from app.clients.spotify import SpotifyError, SpotifyRateLimitError
from app.clients.spotify_user import SpotifyForbiddenError, SpotifyLoginError


def spotify_http_error(error: SpotifyError) -> HTTPException:
    if isinstance(error, SpotifyLoginError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Your Spotify login has expired; open /api/v1/auth/login again"},
        )
    if isinstance(error, SpotifyForbiddenError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Spotify refused this for your account. In Development Mode the "
                "account must be added under Users Management in the Spotify dashboard."
            },
        )
    if isinstance(error, SpotifyRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"message": "Spotify is busy; try again shortly"},
            headers={"Retry-After": str(error.retry_after)},
        )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"message": "Spotify is unavailable right now; try again later"},
    )

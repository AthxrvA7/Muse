"""Turning service errors into clear HTTP errors (no internal details leak)."""

from fastapi import HTTPException, status

from app.clients.spotify import SpotifyError, SpotifyRateLimitError


def spotify_http_error(error: SpotifyError) -> HTTPException:
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

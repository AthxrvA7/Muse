"""Spotify login, logout and the current user."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import Auth, CurrentUser
from app.api.errors import spotify_http_error
from app.clients.spotify import SpotifyError
from app.db.indexes import SESSION_IDLE_SECONDS
from app.schemas.auth import Me
from app.services.auth import SESSION_COOKIE, LoginStateError

router = APIRouter(tags=["auth"])


@router.get("/auth/login", summary="Log in with Spotify (open this in the browser)")
async def login(auth: Auth) -> RedirectResponse:
    return RedirectResponse(await auth.start_login(), status_code=status.HTTP_302_FOUND)


@router.get(
    "/auth/callback", summary="Spotify sends the browser back here", include_in_schema=False
)
async def callback(
    request: Request,
    auth: Auth,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error or not code or not state:
        # e.g. error=access_denied when the user clicks "Cancel" on Spotify's page
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Spotify login was cancelled or failed; please try again"},
        )
    try:
        session_id, _ = await auth.finish_login(code, state)
    except LoginStateError as failure:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"message": str(failure)}
        ) from failure
    except SpotifyError as failure:
        raise spotify_http_error(failure) from failure

    await auth.logout(request.cookies.get(SESSION_COOKIE))  # end any older session
    settings = request.app.state.settings
    response = RedirectResponse(settings.post_login_redirect, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=SESSION_IDLE_SECONDS,
        httponly=True,  # JavaScript can't read it, so an XSS bug can't steal it
        secure=settings.app_env == "production",  # HTTPS only when deployed
        samesite="lax",  # not sent on cross-site POSTs (plus the Origin check)
        path="/",
    )
    return response


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Log out")
async def logout(request: Request, auth: Auth) -> Response:
    await auth.logout(request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me", summary="The logged-in user")
async def me(user: CurrentUser) -> Me:
    return Me(**user.model_dump())

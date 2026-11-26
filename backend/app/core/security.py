"""Security middleware: response headers, rate limiting and the Origin check.

Each one is small on purpose, so it can be read and explained in full.
"""

import logging
import math
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Swagger UI loads its script and styles from a CDN, so the strict policy below would
# break /docs. The docs pages get every other header, just not the CSP.
_DOCS_PATHS = ("/docs", "/openapi.json")

# The API only returns JSON: nothing on these responses should ever load or run.
_API_CSP = "default-src 'none'; frame-ancestors 'none'"

# The website (/app/) may load only its own files, album art from Spotify's image CDN,
# and call only this server. Inline styles are allowed for React's style attributes.
_WEB_CSP = (
    "default-src 'self'; img-src 'self' data: https://i.scdn.co; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; "
    "media-src 'self' https://*.dzcdn.net; "  # 30-second previews from Deezer's CDN
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds browser security headers to every response (OWASP A02)."""

    def __init__(self, app: object, *, hsts: bool) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.hsts = hsts

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"  # don't guess content types
        headers["X-Frame-Options"] = "DENY"  # no embedding in other sites (clickjacking)
        headers["Referrer-Policy"] = "no-referrer"  # don't leak URLs to other sites
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        path = request.url.path
        if path == "/app" or path.startswith("/app/"):
            headers["Content-Security-Policy"] = _WEB_CSP
        elif not path.startswith(_DOCS_PATHS):
            headers["Content-Security-Policy"] = _API_CSP
        if request.url.path.startswith("/api/"):
            headers["Cache-Control"] = "no-store"  # personal data must not sit in caches
        if self.hsts:
            # HTTPS only from now on (production runs behind HTTPS; never sent locally)
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class FixedWindowRateLimiter:
    """Counts requests per key in fixed one-minute windows, in memory.

    Fixed windows are the simplest correct scheme: each (key, minute) gets a counter,
    and a new minute starts from zero. Memory is fine for Muse's single instance
    (ADR-0001); several instances would need a shared store such as MongoDB or Redis.
    """

    WINDOW_SECONDS = 60
    _MAX_KEYS = 10_000  # old windows are cleared before the table can grow past this

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._counts: dict[str, tuple[int, int]] = {}  # key -> (window number, count)

    def hit(self, key: str, limit: int) -> int | None:
        """Count one request. Returns None if allowed, else seconds until the next window."""
        now = self._clock()
        window = int(now // self.WINDOW_SECONDS)
        if len(self._counts) >= self._MAX_KEYS:
            self._counts = {k: v for k, v in self._counts.items() if v[0] == window}

        current_window, count = self._counts.get(key, (window, 0))
        if current_window != window:
            count = 0
        if count >= limit:
            return max(1, math.ceil((window + 1) * self.WINDOW_SECONDS - now))
        self._counts[key] = (window, count + 1)
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rejects a client with 429 once it goes over its per-minute budget (threat T10)."""

    _EXEMPT = ("/health", "/ready")  # platform health checks must never be throttled

    def __init__(
        self,
        app: object,
        *,
        limiter: FixedWindowRateLimiter,
        default_limit: int,
        prefix_limits: dict[str, int],
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.limiter = limiter
        self.default_limit = default_limit
        self.prefix_limits = prefix_limits

    def _bucket(self, path: str) -> tuple[str, int]:
        for prefix, limit in self.prefix_limits.items():
            if path.startswith(prefix):
                return prefix, limit
        return "default", self.default_limit

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if path in self._EXEMPT or request.method == "OPTIONS":
            return await call_next(request)

        # Behind a proxy (Render), uvicorn's --proxy-headers puts the real client IP here
        client_ip = request.client.host if request.client else "unknown"
        bucket, limit = self._bucket(path)
        retry_after = self.limiter.hit(f"{bucket}:{client_ip}", limit)
        if retry_after is None:
            return await call_next(request)

        logger.warning("rate limit exceeded", extra={"bucket": bucket, "path": path})
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": {"message": "Too many requests; try again shortly"}},
            headers={"Retry-After": str(retry_after)},
        )


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Blocks state-changing requests sent by other websites (CSRF defence, threat T4).

    Once login exists, the browser attaches Muse's session cookie to every request to
    Muse, even one triggered by another website. Browsers always send an ``Origin``
    header on cross-site POST/PUT/PATCH/DELETE requests, so a request whose Origin is
    neither Muse itself nor a listed frontend is refused. Requests without an Origin
    (curl, Postman, server-to-server) carry no browser cookies and are allowed.
    """

    _STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: object, *, allowed_origins: list[str]) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.allowed_origins = set(allowed_origins)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        origin = request.headers.get("origin")
        if request.method not in self._STATE_CHANGING or origin is None:
            return await call_next(request)

        own_origin = f"{request.url.scheme}://{request.url.netloc}"  # e.g. Swagger at /docs
        if origin.rstrip("/") in self.allowed_origins or origin.rstrip("/") == own_origin:
            return await call_next(request)

        logger.warning(
            "cross-site request blocked", extra={"method": request.method, "path": request.url.path}
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": {"message": "Requests from this website are not allowed"}},
        )

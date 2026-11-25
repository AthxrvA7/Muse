"""Security middleware: response headers, rate limiting and the Origin check.

Each one is small on purpose, so it can be read and explained in full.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Swagger UI loads its script and styles from a CDN, so the strict policy below would
# break /docs. The docs pages get every other header, just not the CSP.
_DOCS_PATHS = ("/docs", "/openapi.json")

# The API only returns JSON: nothing on these responses should ever load or run.
_API_CSP = "default-src 'none'; frame-ancestors 'none'"


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
        if not request.url.path.startswith(_DOCS_PATHS):
            headers["Content-Security-Policy"] = _API_CSP
        if request.url.path.startswith("/api/"):
            headers["Cache-Control"] = "no-store"  # personal data must not sit in caches
        if self.hsts:
            # HTTPS only from now on (production runs behind HTTPS; never sent locally)
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

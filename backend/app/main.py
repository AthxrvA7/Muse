"""FastAPI application factory.

``create_app()`` builds a fresh app, so tests can create isolated instances
with their own settings, and production runs ``uvicorn app.main:app``.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from app import __version__
from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.core.security import (
    FixedWindowRateLimiter,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.indexes import ensure_indexes
from app.db.mongo import create_client
from app.schemas.meta import ServiceInfo

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Startup: open the MongoDB client once for the whole process (if configured)
        client = create_client(settings) if settings.mongodb_configured else None
        app.state.db = client[settings.mongodb_db] if client is not None else None
        if app.state.db is not None:
            try:
                await ensure_indexes(app.state.db)
            except PyMongoError as error:
                # Start anyway: /ready reports the database as unavailable until it answers,
                # and the indexes are created on the next start.
                logger.warning(
                    "Could not ensure MongoDB indexes",
                    extra={"error_type": type(error).__name__},
                )
        try:
            yield
        finally:
            # Shutdown: close pooled connections cleanly
            app.state.db = None
            if client is not None:
                await client.close()

    app = FastAPI(
        title="Muse API",
        version=__version__,
        description="Mood-aware music curation on top of Spotify.",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.db = None  # set by the lifespan when MongoDB is configured

    # Middleware runs outside-in in the reverse order of these lines: the last one added
    # sees the request first. Request IDs are outermost so every response, including
    # rejections, gets an ID and an access-log line.
    prefix = settings.api_v1_prefix
    app.add_middleware(
        RateLimitMiddleware,
        limiter=FixedWindowRateLimiter(),
        default_limit=settings.rate_limit_per_minute,
        prefix_limits={
            f"{prefix}/curate": settings.rate_limit_curate_per_minute,
            f"{prefix}/auth": settings.rate_limit_auth_per_minute,
        },
    )
    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,  # never "*"
            allow_credentials=True,  # the session cookie (Spotify login, slice 3)
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Content-Type", "X-Request-ID"],
            max_age=600,
        )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.app_env == "production")
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"], summary="Service information")
    def root() -> ServiceInfo:
        return ServiceInfo(name="Muse API", version=__version__, environment=settings.app_env)

    return app


app = create_app()

"""FastAPI application factory.

``create_app()`` builds a fresh app, so tests can create isolated instances
with their own settings, and production runs ``uvicorn app.main:app``.
"""

from fastapi import FastAPI

from app import __version__
from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware
from app.schemas.meta import ServiceInfo


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Muse API",
        version=__version__,
        description="Mood-aware music curation on top of Spotify.",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings

    app.add_middleware(RequestIDMiddleware)
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["meta"], summary="Service information")
    def root() -> ServiceInfo:
        return ServiceInfo(name="Muse API", version=__version__, environment=settings.app_env)

    return app


app = create_app()

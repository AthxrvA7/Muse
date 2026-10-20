"""Aggregates every v1 route module into one router.

Feature routers (auth, preferences, mood, curate) are included here as they land.
"""

from fastapi import APIRouter

from app.api.v1 import catalog, curate, mood

api_router = APIRouter()
api_router.include_router(mood.router)
api_router.include_router(catalog.router)
api_router.include_router(curate.router)

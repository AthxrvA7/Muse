"""Aggregates every v1 route module into one router.

Feature routers (auth, preferences, mood, curate) are included here as they land.
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    catalog,
    covers,
    curate,
    feedback,
    mood,
    moods,
    playlists,
    preferences,
    previews,
    privacy,
    rewind,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(preferences.router)
api_router.include_router(privacy.router)
api_router.include_router(mood.router)
api_router.include_router(catalog.router)
api_router.include_router(curate.router)
api_router.include_router(playlists.router)
api_router.include_router(previews.router)
api_router.include_router(covers.router)
api_router.include_router(feedback.router)
api_router.include_router(moods.router)
api_router.include_router(rewind.router)

"""Aggregates every v1 route module into one router.

Feature routers (auth, preferences, mood, curate) are included here as they land.
"""

from fastapi import APIRouter

api_router = APIRouter()

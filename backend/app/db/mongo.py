"""The MongoDB connection: opened when the app starts, closed when it stops.

One ``AsyncMongoClient`` is shared by the whole process. It keeps its own pool of
connections and connects lazily, so the app still starts if MongoDB is down;
``/ready`` reports the problem instead (graceful degradation).
"""

import logging

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError

from app.core.config import Settings

logger = logging.getLogger(__name__)


def create_client(settings: Settings) -> AsyncMongoClient:
    """Build the client from settings. No network call happens here."""
    if settings.mongodb_uri is None:
        raise RuntimeError("MongoDB is not configured")
    return AsyncMongoClient(
        settings.mongodb_uri.get_secret_value(),
        appname="muse-backend",
        tz_aware=True,  # dates come back as timezone-aware UTC datetimes
        serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
        connectTimeoutMS=settings.mongodb_timeout_ms,
    )


async def ping(database: AsyncDatabase) -> bool:
    """True if the database answers. Never raises: a failure is logged and reported."""
    try:
        await database.command("ping")
    except PyMongoError as error:
        # Only the error type: driver messages can include host names
        logger.warning("MongoDB ping failed", extra={"error_type": type(error).__name__})
        return False
    return True

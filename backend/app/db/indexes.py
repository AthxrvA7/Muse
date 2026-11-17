"""Indexes for every collection, created at startup.

``create_index`` does nothing if an identical index already exists, so running
this on every start is safe (idempotent).

Two kinds matter here:
- unique: the database itself refuses duplicates (one user per Spotify account).
- TTL ("time to live"): MongoDB deletes a document automatically once the date
  field is older than ``expire_after_seconds``. A background job does this about
  once a minute, so code that needs an exact cut-off also checks the age itself.
"""

import logging
from dataclasses import dataclass

from pymongo.asynchronous.database import AsyncDatabase

logger = logging.getLogger(__name__)

SESSION_IDLE_SECONDS = 7 * 24 * 60 * 60  # a session ends after 7 days without use
OAUTH_STATE_SECONDS = 10 * 60  # a login must finish within 10 minutes


@dataclass(frozen=True)
class IndexSpec:
    collection: str
    field: str
    name: str
    unique: bool = False
    expire_after_seconds: int | None = None


INDEXES: tuple[IndexSpec, ...] = (
    IndexSpec("users", "spotify_id", "spotify_id_unique", unique=True),
    IndexSpec("sessions", "id_hash", "id_hash_unique", unique=True),
    IndexSpec("sessions", "user_id", "user_id"),  # "log out everywhere", account deletion
    IndexSpec("sessions", "last_seen_at", "idle_ttl", expire_after_seconds=SESSION_IDLE_SECONDS),
    IndexSpec("oauth_states", "state", "state_unique", unique=True),
    IndexSpec(
        "oauth_states", "created_at", "pending_ttl", expire_after_seconds=OAUTH_STATE_SECONDS
    ),
    IndexSpec("preferences", "user_id", "user_id_unique", unique=True),
)


async def ensure_indexes(database: AsyncDatabase) -> None:
    """Create every index in ``INDEXES`` (no-op for those that already exist)."""
    for spec in INDEXES:
        options: dict[str, object] = {"name": spec.name, "unique": spec.unique}
        if spec.expire_after_seconds is not None:
            options["expireAfterSeconds"] = spec.expire_after_seconds
        await database[spec.collection].create_index([(spec.field, 1)], **options)
    logger.info("MongoDB indexes ensured", extra={"index_count": len(INDEXES)})

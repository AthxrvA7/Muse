"""The user's rights over their data (FR11): see everything Muse holds, and delete it all.

Muse stores only what the user told it and what it made for them: the account (Spotify ID
and name), the taste profile, login sessions, records of playlists it created, and the IDs
of tracks it recently picked (so playlists don't repeat). Mood
text is never stored, so there is nothing to export or delete for it.
"""

from datetime import UTC, datetime
from typing import Any, Protocol

from app.db.models import PlaylistRecord, Preferences, User


class Users(Protocol):
    async def delete(self, user_id: str) -> bool: ...


class Sessions(Protocol):
    async def delete_all_for_user(self, user_id: str) -> int: ...


class PreferencesStore(Protocol):
    async def get(self, user_id: str) -> Preferences | None: ...
    async def delete(self, user_id: str) -> bool: ...


class PlaylistStore(Protocol):
    async def list_for_user(self, user_id: str, limit: int = 20) -> list[PlaylistRecord]: ...
    async def delete_all_for_user(self, user_id: str) -> int: ...


class RecentPicksStore(Protocol):
    async def get(self, user_id: str) -> list[str]: ...
    async def delete(self, user_id: str) -> bool: ...


class PrivacyService:
    def __init__(
        self,
        users: Users,
        sessions: Sessions,
        preferences: PreferencesStore,
        playlists: PlaylistStore,
        recent: RecentPicksStore | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._preferences = preferences
        self._playlists = playlists
        self._recent = recent

    async def export(self, user: User) -> dict[str, Any]:
        """Everything Muse holds about this user, as plain JSON (tokens are never included)."""
        preferences = await self._preferences.get(user.id)
        playlists = await self._playlists.list_for_user(user.id, limit=1000)
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "account": user.model_dump(mode="json"),
            "preferences": preferences.model_dump(mode="json") if preferences else None,
            "playlists_created_by_muse": [p.model_dump(mode="json") for p in playlists],
            "recently_picked_track_ids": await self._recent.get(user.id) if self._recent else [],
            "not_stored": [
                "the text you type about your mood",
                "your Spotify listening history (top tracks and artists are read when you "
                "curate or import, never stored)",
                "your email address",
            ],
        }

    async def delete_account(self, user: User) -> dict[str, int]:
        """Deletes every document Muse holds for this user; logs out every browser."""
        removed = {
            "playlists": await self._playlists.delete_all_for_user(user.id),
            "preferences": int(await self._preferences.delete(user.id)),
            "sessions": await self._sessions.delete_all_for_user(user.id),
        }
        if self._recent:
            removed["recent_picks"] = int(await self._recent.delete(user.id))
        removed["account"] = int(await self._users.delete(user.id))
        return removed

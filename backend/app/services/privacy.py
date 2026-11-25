"""The user's rights over their data (FR11): see everything Muse holds, and delete it all.

Muse stores only what the user told it and what it made for them: the account (Spotify ID
and name), the taste profile, login sessions and records of playlists it created. Mood
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


class PrivacyService:
    def __init__(
        self,
        users: Users,
        sessions: Sessions,
        preferences: PreferencesStore,
        playlists: PlaylistStore,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._preferences = preferences
        self._playlists = playlists

    async def export(self, user: User) -> dict[str, Any]:
        """Everything Muse holds about this user, as plain JSON (tokens are never included)."""
        preferences = await self._preferences.get(user.id)
        playlists = await self._playlists.list_for_user(user.id, limit=1000)
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "account": user.model_dump(mode="json"),
            "preferences": preferences.model_dump(mode="json") if preferences else None,
            "playlists_created_by_muse": [p.model_dump(mode="json") for p in playlists],
            "not_stored": [
                "the text you type about your mood",
                "your Spotify listening history",
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
        removed["account"] = int(await self._users.delete(user.id))
        return removed

"""The ``playlists`` collection: playlists Muse created in users' Spotify accounts."""

from typing import Any

from pymongo.asynchronous.database import AsyncDatabase

from app.db.models import SCHEMA_VERSION, PlaylistRecord


def _to_record(document: dict[str, Any]) -> PlaylistRecord:
    return PlaylistRecord(
        id=str(document["_id"]),
        user_id=document["user_id"],
        spotify_playlist_id=document["spotify_playlist_id"],
        url=document["url"],
        name=document["name"],
        track_count=document["track_count"],
        created_at=document["created_at"],
    )


class PlaylistRepository:
    def __init__(self, database: AsyncDatabase) -> None:
        self._playlists = database["playlists"]

    async def add(self, record: PlaylistRecord) -> PlaylistRecord:
        result = await self._playlists.insert_one(
            {**record.model_dump(exclude={"id"}), "schema_version": SCHEMA_VERSION}
        )
        return record.model_copy(update={"id": str(result.inserted_id)})

    async def list_for_user(self, user_id: str, limit: int = 20) -> list[PlaylistRecord]:
        cursor = self._playlists.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return [_to_record(document) async for document in cursor]

    async def delete_all_for_user(self, user_id: str) -> int:
        result = await self._playlists.delete_many({"user_id": user_id})
        return result.deleted_count

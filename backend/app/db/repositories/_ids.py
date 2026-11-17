"""Converting between MongoDB ObjectIds and the plain string IDs used in the app."""

from bson import ObjectId
from bson.errors import InvalidId


def to_object_id(value: str) -> ObjectId | None:
    """The ObjectId for ``value``, or None if it is not a valid ID (never raises)."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None

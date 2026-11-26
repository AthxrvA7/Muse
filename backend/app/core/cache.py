"""A small in-memory cache with expiry, shared by the API clients (one per process)."""

import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    """A small in-memory cache with expiry; the oldest entries go first when full."""

    def __init__(self, seconds: float = 24 * 3600, size: int = 20_000) -> None:
        self._seconds = seconds
        self._size = size
        self._items: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None or item[0] < time.monotonic():
            self._items.pop(key, None)
            return None
        self._items.move_to_end(key)
        return item[1]

    def put(self, key: str, value: Any, seconds: float | None = None) -> None:
        """Stores a value; `seconds` overrides the cache's usual lifetime for this one."""
        self._items[key] = (
            time.monotonic() + (self._seconds if seconds is None else seconds),
            value,
        )
        self._items.move_to_end(key)
        while len(self._items) > self._size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

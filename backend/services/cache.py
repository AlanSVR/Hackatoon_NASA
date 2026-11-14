from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from time import monotonic
from typing import Any


class TTLCache:
    """Caché local en memoria, acotada y sin persistir credenciales ni resultados indefinidamente."""

    def __init__(self, ttl_seconds: int = 900, max_entries: int = 64):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._items: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._items.get(key)
            if not record:
                return None
            created_at, value = record
            if monotonic() - created_at > self.ttl_seconds:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return deepcopy(value)

    def put(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._items[key] = (monotonic(), deepcopy(value))
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

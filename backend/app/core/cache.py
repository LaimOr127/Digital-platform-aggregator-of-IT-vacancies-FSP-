"""Небольшой кэш в памяти процесса с временем жизни и вытеснением самых старых записей."""

import time
from collections import OrderedDict
from collections.abc import Callable, Hashable


class TtlCache[V]:
    def __init__(
        self, ttl: float, max_items: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._ttl = ttl
        self._max = max_items
        self._clock = clock
        self._items: OrderedDict[Hashable, tuple[float, V]] = OrderedDict()

    def get(self, key: Hashable) -> V | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if self._clock() - stored_at > self._ttl:
            del self._items[key]
            return None
        self._items.move_to_end(key)
        return value

    def put(self, key: Hashable, value: V) -> None:
        self._items[key] = (self._clock(), value)
        self._items.move_to_end(key)
        while len(self._items) > self._max:
            self._items.popitem(last=False)

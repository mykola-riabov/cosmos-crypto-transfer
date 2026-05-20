"""In-memory TTL caches for network-heavy reads (balances, prices, market data)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, Hashable, Optional, Tuple, TypeVar

T = TypeVar('T')

_caches: Dict[str, 'TTLCache'] = {}


@dataclass
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    """Thread-safe key/value cache with per-entry TTL (monotonic clock)."""

    def __init__(self, default_ttl: float = 30.0) -> None:
        self._default_ttl = float(default_ttl)
        self._store: Dict[Hashable, _Entry] = {}
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def invalidate(self, key: Hashable) -> None:
        with self._lock:
            self._store.pop(key, None)

    def get(self, key: Hashable) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if now >= entry.expires_at:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: Hashable, value: Any, ttl: Optional[float] = None) -> None:
        ttl_sec = self._default_ttl if ttl is None else float(ttl)
        expires_at = time.monotonic() + ttl_sec
        with self._lock:
            self._store[key] = _Entry(value=value, expires_at=expires_at)

    def get_or_fetch(
        self,
        key: Hashable,
        fetcher: Callable[[], T],
        *,
        ttl: Optional[float] = None,
        force: bool = False,
    ) -> Tuple[T, bool]:
        """Return (value, from_cache)."""
        if not force:
            cached = self.get(key)
            if cached is not None:
                return cached, True
        value = fetcher()
        self.set(key, value, ttl=ttl)
        return value, False


def get_cache(name: str, *, default_ttl: float = 30.0) -> TTLCache:
    """Named singleton cache (balances, coingecko, osmosis_market, …)."""
    if name not in _caches:
        _caches[name] = TTLCache(default_ttl=default_ttl)
    return _caches[name]


def clear_all_caches() -> None:
    for cache in _caches.values():
        cache.clear()

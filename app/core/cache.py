"""
Prosty in-memory cache z TTL (Time To Live).

Używamy asyncio.Lock zamiast threading.Lock — wszystkie requesty FastAPI
działają w tym samym event loop, więc asyncio jest właściwe.

Ograniczenia:
- Pamięć: cache znika przy restarcie serwisu
- Skalowalność: nie działa między wieloma instancjami (Render free = 1 instancja)
- Alternatywa gdy będziesz skalować: zamień na Redis + fastapi-cache2
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if datetime.utcnow() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = 30) -> None:
        async with self._lock:
            self._store[key] = (value, datetime.utcnow() + timedelta(seconds=ttl))

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


# Globalny singleton — jeden na cały proces
cache = TTLCache()


# ---------------------------------------------------------------------------
# Helpers — klucze cache i invalidation
# ---------------------------------------------------------------------------

def dashboard_key(user_id: int) -> str:
    return f"dashboard:{user_id}"


def activity_key(user_id: int) -> str:
    return f"activity:{user_id}"


async def invalidate_dashboard(user_id: int) -> None:
    """Wywołaj po każdym write który wpływa na dashboard użytkownika."""
    await cache.delete(dashboard_key(user_id))

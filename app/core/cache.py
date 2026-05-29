"""
Cache abstraction with two backends:
  - Redis (when REDIS_URL is set): survives restarts, works across multiple instances
  - In-memory TTLCache (fallback): no dependencies, fine for a single-instance deploy

Switch by setting REDIS_URL in your environment — no code changes needed.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional


# ---------------------------------------------------------------------------
# In-memory fallback
# ---------------------------------------------------------------------------

class _InMemoryCache:
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


# ---------------------------------------------------------------------------
# Redis-backed cache
# ---------------------------------------------------------------------------

class _RedisCache:
    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as aioredis
        import json as _json

        self._client = aioredis.from_url(redis_url, decode_responses=True)
        self._json = _json

    async def get(self, key: str) -> Optional[Any]:
        import redis.asyncio as aioredis
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            return self._json.loads(raw)
        except (aioredis.RedisError, Exception):
            return None

    async def set(self, key: str, value: Any, ttl: int = 30) -> None:
        import redis.asyncio as aioredis
        try:
            await self._client.set(key, self._json.dumps(value, default=str), ex=ttl)
        except (aioredis.RedisError, Exception):
            pass

    async def delete(self, key: str) -> None:
        import redis.asyncio as aioredis
        try:
            await self._client.delete(key)
        except (aioredis.RedisError, Exception):
            pass


# ---------------------------------------------------------------------------
# Factory — pick backend at startup
# ---------------------------------------------------------------------------

def _build_cache() -> Any:
    from app.core.config import settings
    if settings.REDIS_URL:
        return _RedisCache(settings.REDIS_URL)
    return _InMemoryCache()


cache: Any = _build_cache()


# ---------------------------------------------------------------------------
# Key helpers + invalidation
# ---------------------------------------------------------------------------

def dashboard_key(user_id: int) -> str:
    return f"dashboard:{user_id}"


def activity_key(user_id: int) -> str:
    return f"activity:{user_id}"


async def invalidate_dashboard(user_id: int) -> None:
    await cache.delete(dashboard_key(user_id))

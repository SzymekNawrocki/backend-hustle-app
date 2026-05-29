"""Lazy Arq pool singleton. Returns None when REDIS_URL is not configured."""

from typing import Optional

from app.core.config import settings

_pool: Optional[object] = None


async def get_arq_pool() -> Optional[object]:
    """Return the shared Arq pool, or None if Redis is not configured."""
    global _pool
    if not settings.REDIS_URL:
        return None
    if _pool is None:
        import arq
        from arq.connections import RedisSettings
        _pool = await arq.create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()  # type: ignore[attr-defined]
        _pool = None

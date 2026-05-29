from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def get_user_id_key(request: Request) -> str:
    """
    Per-user rate limiting key. Reads user_id from request.state (set once
    by the logging middleware). Falls back to IP if the request is unauthenticated.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


# Use Redis storage when available so rate-limit counters survive restarts
# and work correctly across multiple instances. Falls back to in-memory.
_storage_uri = settings.REDIS_URL or "memory://"

limiter = Limiter(key_func=get_user_id_key, storage_uri=_storage_uri)

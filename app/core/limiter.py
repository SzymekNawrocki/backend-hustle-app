from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_id_key(request: Request) -> str:
    """
    Per-user rate limiting key. Reads user_id from request.state (set once
    by the logging middleware). Falls back to IP if the request is unauthenticated.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id_key)

from fastapi import Request
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def get_user_id_key(request: Request) -> str:
    """
    Key function for per-user rate limiting.
    Extracts user_id from JWT (Authorization header or cookie).
    Falls back to IP address if token is missing or invalid.
    """
    token: str | None = None

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if not token:
        token = request.cookies.get(settings.AUTH_COOKIE_NAME)

    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except JWTError:
            pass

    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id_key)

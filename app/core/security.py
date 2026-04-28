from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

import hashlib
import secrets

# Using PBKDF2-SHA256 as primary to avoid Bcrypt's 72-byte limit.
# Bcrypt is kept for compatibility with any existing hashes.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_refresh_token() -> str:
    """Generate a cryptographically secure random refresh token (64 hex chars)."""
    return secrets.token_hex(32)

def hash_token(token: str) -> str:
    """SHA-256 hash of a token for safe storage in DB."""
    return hashlib.sha256(token.encode()).hexdigest()

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

import hashlib
import base64

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # SHA256 pre-hashing to bypass Bcrypt 72-byte limit
    # This turns any password into a 44-character base64 string (32 bytes raw)
    pw_hash = hashlib.sha256(plain_password.encode("utf-8")).digest()
    pw_b64 = base64.b64encode(pw_hash).decode("utf-8")
    return pwd_context.verify(pw_b64, hashed_password)

def get_password_hash(password: str) -> str:
    # SHA256 pre-hashing to bypass Bcrypt 72-byte limit
    pw_hash = hashlib.sha256(password.encode("utf-8")).digest()
    pw_b64 = base64.b64encode(pw_hash).decode("utf-8")
    return pwd_context.hash(pw_b64)

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

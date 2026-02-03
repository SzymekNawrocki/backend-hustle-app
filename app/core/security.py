from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

import hashlib
import base64

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    print(f"DEBUG: Verifying password (plain length: {len(plain_password)})")
    # SHA256 pre-hashing
    pw_hash = hashlib.sha256(plain_password.encode("utf-8")).digest()
    pw_b64 = base64.b64encode(pw_hash).decode("utf-8")
    print(f"DEBUG: Pre-hashed length: {len(pw_b64)}")
    return pwd_context.verify(pw_b64, hashed_password)

def get_password_hash(password: str) -> str:
    print(f"DEBUG: Hashing password (length: {len(password)})")
    try:
        # SHA256 pre-hashing
        pw_hash = hashlib.sha256(password.encode("utf-8")).digest()
        pw_b64 = base64.b64encode(pw_hash).decode("utf-8")
        print(f"DEBUG: Pre-hashed length: {len(pw_b64)}")
        
        # Final hash with logout
        result = pwd_context.hash(pw_b64)
        print("DEBUG: Hashing successful")
        return result
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        # Ultimate fallback: if even 44 chars is "too long", try an even shorter hash
        # This shouldn't happen but we need to see if this code is even running
        short_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
        return pwd_context.hash(short_hash)

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

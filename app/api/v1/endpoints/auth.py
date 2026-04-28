from datetime import timedelta, datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.demo_service import reset_demo_data_bg


router = APIRouter()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set both access and refresh token cookies on the response."""
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=int(access_expires.total_seconds()),
        path="/",
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=int(refresh_expires.total_seconds()),
        # Restrict refresh cookie to the refresh endpoint only —
        # browser won't send it to any other route.
        path=f"{settings.API_V1_STR}/auth/refresh",
    )


async def _attach_refresh_token(db: AsyncSession, user: User) -> str:
    """Generate, hash and store a new refresh token for user. Returns raw token."""
    raw = security.create_refresh_token()
    expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    user.refresh_token_hash = security.hash_token(raw)
    user.refresh_token_expires_at = (
        datetime.now(timezone.utc).replace(tzinfo=None) + expires
    )
    await db.commit()
    return raw


@router.post("/register", response_model=UserResponse)
async def register(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserCreate
) -> Any:
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Użytkownik z tym mailem już istnieje.")

    db_obj = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


@router.post("/login", response_model=Token)
@limiter.limit("5/minute", key_func=get_remote_address)
async def login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawny email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Użytkownik nieaktywny")

    access_token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    raw_refresh = await _attach_refresh_token(db, user)
    _set_auth_cookies(response, access_token, raw_refresh)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute", key_func=get_remote_address)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Exchange a valid refresh token cookie for a new access token.
    The refresh cookie is restricted to this path — browsers only send it here.
    """
    raw_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token_hash = security.hash_token(raw_token)
    result = await db.execute(
        select(User).where(User.refresh_token_hash == token_hash)
    )
    user = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not user.refresh_token_expires_at or user.refresh_token_expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    access_token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
        path="/",
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    return current_user


@router.post("/demo-login", response_model=Token)
@limiter.limit("3/minute", key_func=get_remote_address)
async def demo_login(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    DEMO_EMAIL = "guest@demo.com"

    result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
    user = result.scalars().first()

    if not user:
        user = User(
            email=DEMO_EMAIL,
            hashed_password=security.get_password_hash("demo-guest-password-not-needed"),
            full_name="Demo Guest",
            is_demo=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    raw_refresh = await _attach_refresh_token(db, user)
    _set_auth_cookies(response, access_token, raw_refresh)
    background_tasks.add_task(reset_demo_data_bg, user.id)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    # Invalidate the refresh token in DB so it can't be reused after logout
    raw_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if raw_token:
        token_hash = security.hash_token(raw_token)
        result = await db.execute(
            select(User).where(User.refresh_token_hash == token_hash)
        )
        user = result.scalars().first()
        if user:
            user.refresh_token_hash = None
            user.refresh_token_expires_at = None
            await db.commit()

    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=f"{settings.API_V1_STR}/auth/refresh",
    )
    return {"status": "ok"}

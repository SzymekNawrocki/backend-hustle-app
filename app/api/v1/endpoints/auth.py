from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, Request, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    Token,
    UpdateProfileRequest,
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.auth_service import auth_service
from app.services.demo_service import reset_demo_data_bg
from app.services.email_service import email_service


router = APIRouter()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
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
        path=f"{settings.API_V1_STR}/auth/refresh",
    )


@router.post("/register", response_model=UserResponse)
async def register(*, db: AsyncSession = Depends(deps.get_db), user_in: UserCreate) -> Any:
    return await auth_service.register(db, user_in)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute", key_func=get_remote_address)
async def login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    access_token, raw_refresh = await auth_service.login(db, form_data.username, form_data.password)
    _set_auth_cookies(response, access_token, raw_refresh)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute", key_func=get_remote_address)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    from fastapi import HTTPException, status
    raw_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    access_token = await auth_service.validate_refresh_token(db, raw_token)
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
async def read_current_user(current_user: User = Depends(deps.get_current_user)) -> Any:
    return current_user


@router.patch("/me", response_model=UserResponse)
@limiter.limit("20/minute")
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return await auth_service.update_profile(db, current_user, body.full_name)


@router.post("/change-password", status_code=204)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    await auth_service.change_password(db, current_user, body.current_password, body.new_password)
    # Clear auth cookies — user must log in again
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path=f"{settings.API_V1_STR}/auth/refresh")


@router.post("/forgot-password", status_code=200)
@limiter.limit("3/hour", key_func=get_remote_address)
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
) -> dict:
    raw_token = await auth_service.forgot_password(db, body.email)
    if raw_token:
        background_tasks.add_task(email_service.send_password_reset, body.email, raw_token)
    # Always return 200 — no user enumeration
    return {"message": "If that email is registered, a reset link is on its way."}


@router.post("/reset-password", status_code=200)
@limiter.limit("10/hour", key_func=get_remote_address)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> dict:
    await auth_service.reset_password(db, body.token, body.new_password)
    return {"message": "Password reset successful. You can now log in with your new password."}


@router.delete("/me", status_code=204)
@limiter.limit("3/hour")
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> None:
    await auth_service.delete_account(db, current_user, body.password)
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path=f"{settings.API_V1_STR}/auth/refresh")


@router.post("/demo-login", response_model=Token)
@limiter.limit("3/minute", key_func=get_remote_address)
async def demo_login(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    user, access_token, raw_refresh = await auth_service.get_or_create_demo_user(db)
    _set_auth_cookies(response, access_token, raw_refresh)
    background_tasks.add_task(reset_demo_data_bg, user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    raw_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    await auth_service.logout(db, raw_token)
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.REFRESH_COOKIE_NAME, path=f"{settings.API_V1_STR}/auth/refresh")
    return {"status": "ok"}

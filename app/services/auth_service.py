import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core import security
from app.core.config import settings
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.schemas.user import UserCreate


class AuthService:
    async def register(self, db: AsyncSession, user_in: UserCreate) -> User:
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Użytkownik z tym mailem już istnieje.")
        user = User(
            email=user_in.email,
            hashed_password=security.get_password_hash(user_in.password),
            full_name=user_in.full_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def login(self, db: AsyncSession, email: str, password: str) -> tuple[str, str]:
        """Authenticate user and return (access_token, raw_refresh_token)."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user or not security.verify_password(password, user.hashed_password):
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
        raw_refresh = await self.attach_refresh_token(db, user)
        return access_token, raw_refresh

    async def attach_refresh_token(self, db: AsyncSession, user: User) -> str:
        """Generate, hash and store a new refresh token. Returns raw token."""
        raw = security.create_refresh_token()
        user.refresh_token_hash = security.hash_token(raw)
        user.refresh_token_expires_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        await db.commit()
        return raw

    async def validate_refresh_token(self, db: AsyncSession, raw_token: str) -> str:
        """Validate refresh token and return a new access token."""
        token_hash = security.hash_token(raw_token)
        result = await db.execute(select(User).where(User.refresh_token_hash == token_hash))
        user = result.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not user.refresh_token_expires_at or user.refresh_token_expires_at < now:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        return security.create_access_token(
            user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

    async def logout(self, db: AsyncSession, raw_token: str | None) -> None:
        if not raw_token:
            return
        token_hash = security.hash_token(raw_token)
        result = await db.execute(select(User).where(User.refresh_token_hash == token_hash))
        user = result.scalars().first()
        if user:
            user.refresh_token_hash = None
            user.refresh_token_expires_at = None
            await db.commit()

    async def get_or_create_demo_user(self, db: AsyncSession) -> tuple[User, str, str]:
        """Return (user, access_token, raw_refresh_token) for the demo account."""
        DEMO_EMAIL = "guest@demo.com"
        result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        user = result.scalars().first()
        if not user:
            user = User(
                email=DEMO_EMAIL,
                hashed_password=security.get_password_hash("demo-guest-password-not-needed"),
                full_name="Demo Guest",
                is_demo=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        access_token = security.create_access_token(
            user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        raw_refresh = await self.attach_refresh_token(db, user)
        return user, access_token, raw_refresh

    async def update_profile(self, db: AsyncSession, user: User, full_name: str) -> User:
        user.full_name = full_name
        await db.commit()
        await db.refresh(user)
        return user

    async def change_password(
        self, db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> None:
        if not security.verify_password(current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        user.hashed_password = security.get_password_hash(new_password)
        # Invalidate refresh token so other sessions are logged out
        user.refresh_token_hash = None
        user.refresh_token_expires_at = None
        await db.commit()

    async def forgot_password(self, db: AsyncSession, email: str) -> str | None:
        """Create a reset token and return raw token if user exists, else None."""
        result = await db.execute(select(User).where(User.email == email, User.is_active == True))  # noqa: E712
        user = result.scalars().first()
        if not user or user.is_demo:
            return None

        # Expire any existing unused tokens for this user
        await db.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )

        raw_token = secrets.token_urlsafe(32)
        token_hash = security.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()
        return raw_token

    async def reset_password(self, db: AsyncSession, raw_token: str, new_password: str) -> None:
        token_hash = security.hash_token(raw_token)
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        reset_token = result.scalars().first()

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if not reset_token or reset_token.used_at is not None or reset_token.expires_at < now:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
        user = user_result.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user.hashed_password = security.get_password_hash(new_password)
        user.refresh_token_hash = None
        user.refresh_token_expires_at = None
        reset_token.used_at = now
        await db.commit()

    async def delete_account(self, db: AsyncSession, user: User, password: str) -> None:
        if user.is_demo:
            raise HTTPException(status_code=403, detail="Demo account cannot be deleted")
        if not security.verify_password(password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")
        await db.delete(user)
        await db.commit()


auth_service = AuthService()

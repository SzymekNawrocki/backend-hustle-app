from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core import security
from app.core.config import settings
from app.models.user import User
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


auth_service = AuthService()

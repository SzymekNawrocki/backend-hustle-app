from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Hustle App"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        # asyncpg doesn't support sslmode or channel_binding in the DSN string
        if "?" in url:
            base_url = url.split("?")[0]
            return base_url
        return url

    SECRET_KEY: str

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long. "
                "Generate one with: openssl rand -hex 32"
            )
        return v
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_COOKIE_NAME: str = "refresh_token"
    GROQ_API_KEY: str

    # True for Neon/production (requires SSL). False for local postgres.
    DB_SSL: bool = True

    SENTRY_DSN: Optional[str] = None

    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "Hustle App <noreply@hustle-app.dev>"

    # Frontend base URL (used in email links)
    FRONTEND_URL: str = "https://hustle-app-theta.vercel.app"

    # Stripe (optional — Phase 2 donations)
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Redis (optional — Phase 3: persistent cache + rate limiting + Arq jobs)
    REDIS_URL: Optional[str] = None

    AUTH_COOKIE_NAME: str = "token"
    # MUST be True for cross-site production (Vercel -> Render)
    AUTH_COOKIE_SECURE: bool = True
    # MUST be "none" for cross-site cookies to be sent
    AUTH_COOKIE_SAMESITE: str = "none"
    BACKEND_CORS_ORIGINS: list[str] = [
        "https://hustle-app-theta.vercel.app",
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

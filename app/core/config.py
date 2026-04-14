from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "HustleOS"
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
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str

    AUTH_COOKIE_NAME: str = "token"
    # For localhost/dev keep False. For cross-site production typically True with SameSite=None.
    AUTH_COOKIE_SECURE: bool = False
    # Allowed values: "lax", "strict", "none"
    AUTH_COOKIE_SAMESITE: str = "lax"
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

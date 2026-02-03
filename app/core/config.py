from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "HustleOS"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GROQ_API_KEY: str
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

"""
Integration test fixtures — spin up a real PostgreSQL container, run migrations,
yield a session per test, roll back after.

Requires Docker (available on GitHub Actions ubuntu-latest).
Skip locally with: pytest --ignore=tests/integration
"""

import os
import subprocess
import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_url(postgres_container: PostgresContainer) -> str:
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session", autouse=True)
def run_migrations(db_url: str):
    """Apply all Alembic migrations against the test container."""
    sync_url = db_url.replace("+asyncpg", "").replace("postgresql+psycopg2", "postgresql")
    env = {
        **os.environ,
        "DATABASE_URL": sync_url,
        "SECRET_KEY": "integration-test-secret-key-must-be-32-chars",
        "GROQ_API_KEY": "test-groq-key",
        "DB_SSL": "false",
        "AUTH_COOKIE_SECURE": "false",
    }
    result = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic migration failed:\n{result.stderr}")


@pytest_asyncio.fixture
async def db(db_url: str):
    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://").replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(async_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()

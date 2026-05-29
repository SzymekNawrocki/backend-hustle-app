"""
Integration tests — run against a real PostgreSQL container.
Cover the full user lifecycle: register → login → create goal → dashboard → delete account.
"""

import os

os.environ.setdefault("SECRET_KEY", "integration-test-secret-key-must-be-32-chars")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("DB_SSL", "false")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.user import User
from app.models.goal import Goal
from app.schemas.user import UserCreate
from app.schemas.goal import GoalCreate
from app.services.auth_service import AuthService
from app.services.goal_service import GoalService


@pytest.mark.asyncio
async def test_register_creates_user(db):
    svc = AuthService()
    user_in = UserCreate(email="test_reg@example.com", password="password123", full_name="Test User")
    user = await svc.register(db, user_in)
    assert user.id is not None
    assert user.email == "test_reg@example.com"
    assert user.full_name == "Test User"


@pytest.mark.asyncio
async def test_login_returns_tokens(db):
    svc = AuthService()
    await svc.register(db, UserCreate(email="test_login@example.com", password="pass1234!", full_name="Login User"))
    access_token, refresh_token = await svc.login(db, "test_login@example.com", "pass1234!")
    assert access_token
    assert refresh_token


@pytest.mark.asyncio
async def test_create_goal_stored_in_db(db):
    auth_svc = AuthService()
    goal_svc = GoalService()

    user = await auth_svc.register(db, UserCreate(email="test_goal@example.com", password="pass1234!", full_name="Goal User"))
    goal_in = GoalCreate(title="Learn Python", category="PERSONAL")
    result = await goal_svc.create(db, user.id, goal_in)

    assert result["title"] == "Learn Python"
    assert result["id"] is not None


@pytest.mark.asyncio
async def test_dashboard_returns_correct_counts(db):
    auth_svc = AuthService()
    goal_svc = GoalService()

    user = await auth_svc.register(db, UserCreate(email="test_dash@example.com", password="pass1234!", full_name="Dash User"))
    await goal_svc.create(db, user.id, GoalCreate(title="Goal 1", category="CAREER"))
    await goal_svc.create(db, user.id, GoalCreate(title="Goal 2", category="FINANCE"))

    dashboard = await goal_svc.get_dashboard_today(db, user.id)
    assert dashboard["total_goals"] >= 2


@pytest.mark.asyncio
async def test_delete_account_removes_user_and_cascades(db):
    auth_svc = AuthService()
    goal_svc = GoalService()

    user = await auth_svc.register(db, UserCreate(email="test_del@example.com", password="delete_me!", full_name="Delete Me"))
    await goal_svc.create(db, user.id, GoalCreate(title="Orphan goal", category="PERSONAL"))

    user_id = user.id
    await auth_svc.delete_account(db, user, "delete_me!")

    result = await db.execute(select(User).where(User.id == user_id))
    assert result.scalars().first() is None

    result = await db.execute(select(Goal).where(Goal.user_id == user_id))
    assert result.scalars().first() is None

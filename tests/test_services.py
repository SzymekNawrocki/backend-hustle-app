"""
Integration-style tests for GoalService and AuthService.

Uses AsyncMock to isolate service logic from the database, testing the
business rules that used to be buried inside endpoint functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.core.exceptions import AIServiceError
from app.services.goal_service import GoalService
from app.services.auth_service import AuthService
from app.models.goal import Goal, Task, Milestone
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalUpdate, SmartCreateInput
from app.schemas.user import UserCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _scalar_result(value):
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    return result


# ---------------------------------------------------------------------------
# GoalService — get (404 path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_goal_service_get_raises_404_when_not_found():
    svc = GoalService()
    db = _mock_db()
    db.execute.return_value = _scalar_result(None)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get(db, user_id=1, goal_id=99)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_goal_service_get_returns_goal_when_found():
    svc = GoalService()
    db = _mock_db()
    goal = MagicMock(spec=Goal)
    goal.id = 1
    goal.user_id = 1
    goal.deleted_at = None
    db.execute.return_value = _scalar_result(goal)

    result = await svc.get(db, user_id=1, goal_id=1)
    assert result is goal


# ---------------------------------------------------------------------------
# GoalService — delete (soft-delete cascade)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_goal_service_delete_raises_404_when_not_found():
    svc = GoalService()
    db = _mock_db()
    db.execute.return_value = _scalar_result(None)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete(db, user_id=1, goal_id=99)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_goal_service_delete_soft_deletes_goal_and_tasks():
    svc = GoalService()
    db = _mock_db()

    task1 = MagicMock(spec=Task)
    task1.soft_delete = MagicMock()
    task2 = MagicMock(spec=Task)
    task2.soft_delete = MagicMock()

    goal = MagicMock(spec=Goal)
    goal.tasks = [task1, task2]
    goal.soft_delete = MagicMock()

    db.execute.return_value = _scalar_result(goal)

    with patch("app.services.goal_service.invalidate_dashboard", new_callable=AsyncMock):
        await svc.delete(db, user_id=1, goal_id=1)

    goal.soft_delete.assert_called_once()
    task1.soft_delete.assert_called_once()
    task2.soft_delete.assert_called_once()
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# GoalService — toggle_task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_toggle_task_raises_404_when_not_found():
    svc = GoalService()
    db = _mock_db()
    db.execute.return_value = _scalar_result(None)

    with pytest.raises(HTTPException) as exc_info:
        await svc.toggle_task(db, user_id=1, task_id=99)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_toggle_task_flips_completion():
    svc = GoalService()
    db = _mock_db()

    task = MagicMock(spec=Task)
    task.is_completed = False
    db.execute.return_value = _scalar_result(task)

    with patch("app.services.goal_service.invalidate_dashboard", new_callable=AsyncMock):
        await svc.toggle_task(db, user_id=1, task_id=1)

    assert task.is_completed is True


# ---------------------------------------------------------------------------
# GoalService — smart_create (AI error path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_smart_create_raises_503_on_ai_error():
    svc = GoalService()
    db = _mock_db()

    with patch("app.services.goal_service.ai_service") as mock_ai:
        mock_ai.generate_okr = AsyncMock(side_effect=AIServiceError("unavailable", 503))
        with pytest.raises(HTTPException) as exc_info:
            await svc.smart_create(db, user_id=1, idea="build a startup")

    assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# AuthService — login (wrong password)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_service_login_raises_401_on_bad_password():
    svc = AuthService()
    db = _mock_db()

    user = MagicMock(spec=User)
    user.is_active = True
    user.hashed_password = "hashed"
    db.execute.return_value = _scalar_result(user)

    with patch("app.services.auth_service.security.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await svc.login(db, "user@example.com", "wrong")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_service_login_raises_401_when_user_not_found():
    svc = AuthService()
    db = _mock_db()
    db.execute.return_value = _scalar_result(None)

    with pytest.raises(HTTPException) as exc_info:
        await svc.login(db, "nobody@example.com", "pass")

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# AuthService — validate_refresh_token (expired)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_refresh_token_raises_401_when_expired():
    from datetime import datetime, timezone, timedelta
    svc = AuthService()
    db = _mock_db()

    user = MagicMock(spec=User)
    user.is_active = True
    user.refresh_token_expires_at = (
        datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    )
    db.execute.return_value = _scalar_result(user)

    with patch("app.services.auth_service.security.hash_token", return_value="hashed"):
        with pytest.raises(HTTPException) as exc_info:
            await svc.validate_refresh_token(db, "raw_token")

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_validate_refresh_token_raises_401_when_user_not_found():
    svc = AuthService()
    db = _mock_db()
    db.execute.return_value = _scalar_result(None)

    with patch("app.services.auth_service.security.hash_token", return_value="hashed"):
        with pytest.raises(HTTPException) as exc_info:
            await svc.validate_refresh_token(db, "raw_token")

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# AuthService — register (duplicate email)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_raises_400_on_duplicate_email():
    svc = AuthService()
    db = _mock_db()

    existing = MagicMock(spec=User)
    db.execute.return_value = _scalar_result(existing)

    with pytest.raises(HTTPException) as exc_info:
        await svc.register(db, UserCreate(email="a@b.com", password="pass123", full_name="A"))

    assert exc_info.value.status_code == 400

from typing import Any
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.goal import (
    GoalCreate, GoalResponse, GoalUpdate, DashboardToday,
    SmartCreateInput, TaskResponse, MilestoneResponse, ActivityHistory,
)
from app.schemas.pagination import PaginatedResponse
from app.services.goal_service import goal_service

router = APIRouter()


@router.post("/", response_model=GoalResponse)
async def create_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_in: GoalCreate,
) -> Any:
    return await goal_service.create(db, current_user.id, goal_in)


@router.get("/", response_model=PaginatedResponse[GoalResponse])
async def read_goals(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    return await goal_service.list(db, current_user.id, page, limit)


@router.get("/dashboard/today", response_model=DashboardToday)
async def get_dashboard_today(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return await goal_service.get_dashboard(db, current_user.id)


@router.get("/activity/history", response_model=ActivityHistory)
async def get_activity_history(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return await goal_service.get_activity_history(db, current_user.id)


@router.post("/smart-create", response_model=GoalResponse)
@limiter.limit("10/minute")
async def smart_create_goal(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    input_data: SmartCreateInput = ...,
) -> Any:
    return await goal_service.smart_create(db, current_user.id, input_data.idea)


@router.get("/{goal_id}", response_model=GoalResponse)
async def read_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_id: int,
) -> Any:
    return await goal_service.get(db, current_user.id, goal_id)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_id: int,
    goal_in: GoalUpdate,
) -> Any:
    return await goal_service.update(db, current_user.id, goal_id, goal_in)


@router.delete("/{goal_id}", response_model=GoalResponse)
async def delete_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_id: int,
) -> Any:
    return await goal_service.delete(db, current_user.id, goal_id)


@router.post("/tasks/{task_id}/toggle", response_model=TaskResponse)
async def toggle_task(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    task_id: int,
) -> Any:
    return await goal_service.toggle_task(db, current_user.id, task_id)


@router.post("/milestones/{milestone_id}/toggle", response_model=MilestoneResponse)
async def toggle_milestone(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    milestone_id: int,
) -> Any:
    return await goal_service.toggle_milestone(db, current_user.id, milestone_id)

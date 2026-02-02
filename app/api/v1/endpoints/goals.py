from datetime import datetime, date
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.goal import Goal, Milestone, Task, Habit
from app.schemas.goal import (
    GoalCreate, GoalResponse, DashboardToday, SmartCreateInput,
    TaskResponse, HabitResponse, MilestoneCreate, GoalUpdate, GoalBase
)
from app.schemas.ai import OKRAIResponse
from app.services.ai_service import ai_service

router = APIRouter()

@router.post("/", response_model=GoalResponse)
async def create_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_in: GoalCreate
) -> Any:
    """
    Create new goal with optional milestones.
    """
    db_goal = Goal(
        title=goal_in.title,
        description=goal_in.description,
        category=goal_in.category,
        target_date=goal_in.target_date,
        status=goal_in.status,
        user_id=current_user.id
    )
    db.add(db_goal)
    await db.flush() # Get id
    
    if goal_in.milestones:
        for milestone_in in goal_in.milestones:
            db_milestone = Milestone(
                title=milestone_in.title,
                is_completed=milestone_in.is_completed,
                goal_id=db_goal.id
            )
            db.add(db_milestone)
    
    await db.commit()
    # Reload with milestones
    result = await db.execute(
        select(Goal).where(Goal.id == db_goal.id).options(selectinload(Goal.milestones))
    )
    return result.scalars().first()

@router.get("/", response_model=List[GoalResponse])
async def read_goals(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve goals for current user.
    """
    result = await db.execute(
        select(Goal)
        .where(Goal.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .options(selectinload(Goal.milestones))
    )
    return result.scalars().all()

@router.get("/dashboard/today", response_model=DashboardToday)
async def get_dashboard_today(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get tasks due today and all habits for the dashboard.
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    tasks_result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.due_date >= today_start,
            Task.due_date <= today_end
        )
    )
    tasks = tasks_result.scalars().all()
    
    habits_result = await db.execute(
        select(Habit).where(Habit.user_id == current_user.id)
    )
    habits = habits_result.scalars().all()
    
    return {
        "tasks": tasks,
        "habits": habits
    }

@router.post("/smart-create", response_model=GoalResponse)
async def smart_create_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    input_data: SmartCreateInput
) -> Any:
    """
    Generate a smart goal and milestones using AI based on an idea.
    """
    ai_data = await ai_service.generate_okr(input_data.idea)
    
    if "error" in ai_data:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=ai_data.get("details", "AI Error"))
    
    try:
        okr = OKRAIResponse(**ai_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI output validation failed: {e}")

    db_goal = Goal(
        title=okr.title,
        description=f"AI-generated goal based on: {input_data.idea}",
        user_id=current_user.id
    )
    db.add(db_goal)
    await db.flush()
    
    for m_title in okr.milestones:
        db.add(Milestone(title=m_title, goal_id=db_goal.id))
    
    await db.commit()
    result = await db.execute(
        select(Goal).where(Goal.id == db_goal.id).options(selectinload(Goal.milestones))
    )
    return result.scalars().first()

@router.get("/{goal_id}", response_model=GoalResponse)
async def read_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_id: int
) -> Any:
    """
    Get a specific goal by ID.
    """
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
        .options(selectinload(Goal.milestones))
    )
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_id: int,
    goal_in: GoalUpdate
) -> Any:
    """
    Update a goal.
    """
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
        .options(selectinload(Goal.milestones))
    )
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    update_data = goal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)
    
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal

@router.delete("/{goal_id}", response_model=GoalResponse)
async def delete_goal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    goal_id: int
) -> Any:
    """
    Delete a goal.
    """
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
        .options(selectinload(Goal.milestones))
    )
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    await db.delete(goal)
    await db.commit()
    return goal

import asyncio
from datetime import datetime, date, timedelta, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.core.limiter import limiter
from app.db.pagination import paginate
from app.schemas.pagination import PaginatedResponse
from app.models.user import User
from app.models.goal import Goal, Milestone, Task, Habit, GoalStatus
from app.models.finance import Expense, ExpenseCategory
from app.models.health import MealLog
from app.models.job_offer import JobOffer
from sqlalchemy import func, desc, case, cast, Date as SQLDate
from app.schemas.goal import (
    GoalCreate, GoalResponse, DashboardToday, SmartCreateInput,
    TaskResponse, MilestoneResponse, GoalUpdate, ActivityHistory, ActivityDay
)
from app.schemas.ai import OKRAIResponse
from app.services.ai_service import ai_service
from app.core.cache import cache, dashboard_key, activity_key, invalidate_dashboard

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
    obj_id = db_goal.id

    if goal_in.milestones:
        for milestone_in in goal_in.milestones:
            db_milestone = Milestone(
                title=milestone_in.title,
                is_completed=milestone_in.is_completed,
                goal_id=obj_id
            )
            db.add(db_milestone)

    await db.commit()
    await invalidate_dashboard(current_user.id)
    # Reload with milestones using the local ID
    result = await db.execute(
        select(Goal).where(Goal.id == obj_id).options(selectinload(Goal.milestones))
    )
    db_goal_final = result.scalars().first()
    return GoalResponse.model_validate(db_goal_final).model_dump()

@router.get("/", response_model=PaginatedResponse[GoalResponse])
async def read_goals(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    base_filter = (Goal.user_id == current_user.id, Goal.deleted_at.is_(None))
    return await paginate(
        db,
        query=select(Goal).where(*base_filter).options(
            selectinload(Goal.milestones), selectinload(Goal.tasks)
        ),
        count_query=select(func.count(Goal.id)).where(*base_filter),
        page=page,
        limit=limit,
    )


@router.get("/dashboard/today", response_model=DashboardToday)
async def get_dashboard_today(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get dashboard summary including today's tasks/meals and recent activity.
    """
    cached = await cache.get(dashboard_key(current_user.id))
    if cached is not None:
        return cached

    uid = current_user.id
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    # All 8 queries are independent — run them concurrently
    (
        tasks_r, habits_r, balance_r, meals_r,
        goals_count_r, offers_r, expenses_r, latest_goal_r,
    ) = await asyncio.gather(
        db.execute(select(Task).where(
            Task.user_id == uid,
            Task.due_date >= today_start,
            Task.due_date <= today_end,
            Task.deleted_at.is_(None),
        )),
        db.execute(select(Habit).where(Habit.user_id == uid)),
        db.execute(select(func.sum(
            case((Expense.category == ExpenseCategory.INCOME, Expense.amount), else_=-Expense.amount)
        )).where(Expense.user_id == uid, Expense.deleted_at.is_(None))),
        db.execute(select(MealLog).where(
            MealLog.user_id == uid,
            MealLog.created_at >= today_start,
            MealLog.created_at <= today_end,
            MealLog.deleted_at.is_(None),
        )),
        db.execute(select(func.count(Goal.id)).where(
            Goal.user_id == uid,
            Goal.status == GoalStatus.IN_PROGRESS,
            Goal.deleted_at.is_(None),
        )),
        db.execute(select(JobOffer)
            .where(JobOffer.user_id == uid, JobOffer.deleted_at.is_(None))
            .order_by(desc(JobOffer.id)).limit(5)),
        db.execute(select(Expense)
            .where(Expense.user_id == uid, Expense.deleted_at.is_(None))
            .order_by(desc(Expense.timestamp)).limit(5)),
        db.execute(select(Goal)
            .where(Goal.user_id == uid, Goal.deleted_at.is_(None))
            .order_by(desc(Goal.id)).limit(1)
            .options(selectinload(Goal.milestones), selectinload(Goal.tasks))),
    )

    today_meals = meals_r.scalars().all()

    dashboard = DashboardToday.model_validate({
        "tasks": tasks_r.scalars().all(),
        "habits": habits_r.scalars().all(),
        "finance_balance": balance_r.scalar() or 0.0,
        "health_calories": sum(m.calories or 0.0 for m in today_meals),
        "active_goals_count": goals_count_r.scalar() or 0,
        "recent_offers": offers_r.scalars().all(),
        "today_meals": today_meals,
        "recent_expenses": expenses_r.scalars().all(),
        "latest_goal": latest_goal_r.scalars().first(),
    })
    await cache.set(dashboard_key(current_user.id), dashboard, ttl=30)
    return dashboard

@router.get("/activity/history", response_model=ActivityHistory)
async def get_activity_history(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get 7-day activity history for the dashboard chart.
    """
    cached = await cache.get(activity_key(current_user.id))
    if cached is not None:
        return cached

    uid = current_user.id
    seven_days_ago = date.today() - timedelta(days=6)
    since = datetime.combine(seven_days_ago, datetime.min.time())

    # All 3 queries are independent — run them concurrently
    goals_count_r, finance_rows, health_rows = await asyncio.gather(
        db.execute(select(func.count(Goal.id)).where(
            Goal.user_id == uid,
            Goal.status == GoalStatus.IN_PROGRESS,
            Goal.deleted_at.is_(None),
        )),
        db.execute(
            select(
                cast(Expense.timestamp, SQLDate).label("day"),
                func.sum(case(
                    (Expense.category == ExpenseCategory.INCOME, Expense.amount),
                    else_=-Expense.amount
                )).label("balance")
            )
            .where(Expense.user_id == uid, Expense.timestamp >= since, Expense.deleted_at.is_(None))
            .group_by(cast(Expense.timestamp, SQLDate))
        ),
        db.execute(
            select(
                cast(MealLog.created_at, SQLDate).label("day"),
                func.coalesce(func.sum(MealLog.calories), 0.0).label("calories")
            )
            .where(MealLog.user_id == uid, MealLog.created_at >= since, MealLog.deleted_at.is_(None))
            .group_by(cast(MealLog.created_at, SQLDate))
        ),
    )

    active_goals_count = goals_count_r.scalar() or 0
    finance_map = {row.day: float(row.balance) for row in finance_rows}
    health_map = {row.day: float(row.calories) for row in health_rows}

    days = [
        ActivityDay(
            date=(date.today() - timedelta(days=i)).strftime("%d/%m"),
            finance=finance_map.get(date.today() - timedelta(days=i), 0.0),
            health=health_map.get(date.today() - timedelta(days=i), 0.0),
            goals=active_goals_count,
        )
        for i in range(6, -1, -1)
    ]

    activity = ActivityHistory(days=days)
    await cache.set(activity_key(current_user.id), activity, ttl=60)
    return activity

@router.post("/smart-create", response_model=GoalResponse)
@limiter.limit("10/minute")
async def smart_create_goal(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    input_data: SmartCreateInput = ...,
) -> Any:
    """
    Generate a smart goal and milestones using AI based on an idea.
    """
    ai_data = await ai_service.generate_okr(input_data.idea)

    if "error" in ai_data:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=ai_data.get("details", "AI Error"))

    # Ensure all required fields exist for OKRAIResponse
    if "title" not in ai_data:
        ai_data["title"] = input_data.idea[:50]
    if "description" not in ai_data:
        ai_data["description"] = f"Plan for: {input_data.idea}"
    if "milestones" not in ai_data or not isinstance(ai_data["milestones"], list):
        ai_data["milestones"] = ["Project kickoff", "Execute key steps", "Wrap up"]
    if "tasks" not in ai_data or not isinstance(ai_data["tasks"], list):
        ai_data["tasks"] = ["Define the first step", "Prepare the tools", "Take action!"]

    try:
        okr = OKRAIResponse(**ai_data)
    except Exception:
        # Final fallback if even defaults are weird
        okr = OKRAIResponse(
            title=ai_data.get("title", "New goal"),
            description=ai_data.get("description", "No description"),
            milestones=ai_data.get("milestones", []),
            tasks=ai_data.get("tasks", [])
        )

    db_goal = Goal(
        title=okr.title,
        description=okr.description,
        user_id=current_user.id
    )
    db.add(db_goal)
    await db.flush()

    for m_title in okr.milestones:
        db.add(Milestone(title=m_title, goal_id=db_goal.id))

    for t_title in okr.tasks:
        db.add(Task(title=t_title, goal_id=db_goal.id, user_id=current_user.id))

    await db.commit()

    # Reload with full data for response
    result = await db.execute(
        select(Goal)
        .where(Goal.id == db_goal.id)
        .options(
            selectinload(Goal.milestones),
            selectinload(Goal.tasks)
        )
    )
    db_goal_final = result.scalars().first()
    return GoalResponse.model_validate(db_goal_final).model_dump()

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
        .where(Goal.id == goal_id, Goal.user_id == current_user.id, Goal.deleted_at.is_(None))
        .options(
            selectinload(Goal.milestones),
            selectinload(Goal.tasks)
        )
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
        .where(Goal.id == goal_id, Goal.user_id == current_user.id, Goal.deleted_at.is_(None))
        .options(selectinload(Goal.milestones))
    )
    goal = result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    update_data = goal_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(goal, field, value)

    db.add(goal)
    await db.flush()
    obj_id = goal.id
    await db.commit()
    await invalidate_dashboard(current_user.id)

    # Reload with relationships
    result = await db.execute(
        select(Goal)
        .where(Goal.id == obj_id)
        .options(
            selectinload(Goal.milestones),
            selectinload(Goal.tasks)
        )
    )
    db_goal_final = result.scalars().first()
    return GoalResponse.model_validate(db_goal_final).model_dump()

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
        .where(Goal.id == goal_id, Goal.user_id == current_user.id, Goal.deleted_at.is_(None))
        .options(
            selectinload(Goal.milestones),
            selectinload(Goal.tasks)
        )
    )
    goal_to_return = result.scalars().first()
    if not goal_to_return:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal_to_return.soft_delete()
    for task in goal_to_return.tasks:
        task.soft_delete()
    await db.commit()
    await invalidate_dashboard(current_user.id)
    return goal_to_return
@router.post("/tasks/{task_id}/toggle", response_model=TaskResponse)
async def toggle_task(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    task_id: int
) -> Any:
    """
    Toggle task completion status.
    """
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
            Task.deleted_at.is_(None),
        )
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_completed = not task.is_completed
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await invalidate_dashboard(current_user.id)
    return task

@router.post("/milestones/{milestone_id}/toggle", response_model=MilestoneResponse)
async def toggle_milestone(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    milestone_id: int
) -> Any:
    """
    Toggle milestone completion status.
    """
    # Join with Goal to check user_id
    result = await db.execute(
        select(Milestone)
        .join(Goal)
        .where(Milestone.id == milestone_id, Goal.user_id == current_user.id)
    )
    milestone = result.scalars().first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    milestone.is_completed = not milestone.is_completed
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    await invalidate_dashboard(current_user.id)
    return milestone

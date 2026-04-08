from datetime import datetime, date, timedelta
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.goal import Goal, Milestone, Task, Habit, GoalStatus
from app.models.finance import Expense, ExpenseCategory
from app.models.health import MealLog
from app.models.job_offer import JobOffer
from sqlalchemy import func, desc
from app.schemas.goal import (
    GoalCreate, GoalResponse, DashboardToday, SmartCreateInput,
    TaskResponse, HabitResponse, MilestoneCreate, MilestoneResponse, GoalUpdate, GoalBase,
    ActivityHistory, ActivityDay
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
    # Reload with milestones using the local ID
    result = await db.execute(
        select(Goal).where(Goal.id == obj_id).options(selectinload(Goal.milestones))
    )
    db_goal_final = result.scalars().first()
    return GoalResponse.model_validate(db_goal_final).model_dump()

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
        .options(
            selectinload(Goal.milestones),
            selectinload(Goal.tasks)
        )
    )
    goals = result.scalars().all()
    print(f"DEBUG: read_goals for user {current_user.id} found {len(goals)} goals")
    return goals


@router.get("/dashboard/today", response_model=DashboardToday)
async def get_dashboard_today(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get dashboard summary including today's tasks/meals and recent activity.
    """
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())
    
    # Today's Tasks
    tasks_result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.due_date >= today_start,
            Task.due_date <= today_end
        )
    )
    tasks = tasks_result.scalars().all()
    
    # Habits
    habits_result = await db.execute(
        select(Habit).where(Habit.user_id == current_user.id)
    )
    habits = habits_result.scalars().all()
    
    # Total Financial Balance (Current state)
    all_expenses_result = await db.execute(
        select(Expense).where(Expense.user_id == current_user.id)
    )
    all_expenses = all_expenses_result.scalars().all()
    total_balance = sum(
        e.amount if e.category == ExpenseCategory.INCOME else -e.amount 
        for e in all_expenses
    )

    # Today's Calories
    today_meals_result = await db.execute(
        select(MealLog).where(
            MealLog.user_id == current_user.id,
            MealLog.created_at >= today_start,
            MealLog.created_at <= today_end
        )
    )
    today_meals = today_meals_result.scalars().all()
    health_calories = sum(m.calories or 0.0 for m in today_meals)

    # Active Goals Count
    goals_count_result = await db.execute(
        select(func.count(Goal.id)).where(
            Goal.user_id == current_user.id,
            Goal.status == GoalStatus.IN_PROGRESS
        )
    )
    active_goals_count = goals_count_result.scalar() or 0

    # Recent Job Offers (Last 5)
    offers_result = await db.execute(
        select(JobOffer).where(JobOffer.user_id == current_user.id)
        .order_by(desc(JobOffer.id))
        .limit(5)
    )
    recent_offers = offers_result.scalars().all()

    # Recent Expenses (Last 5)
    recent_expenses_result = await db.execute(
        select(Expense).where(Expense.user_id == current_user.id)
        .order_by(desc(Expense.timestamp))
        .limit(5)
    )
    recent_expenses = recent_expenses_result.scalars().all()

    # Latest Goal
    latest_goal_result = await db.execute(
        select(Goal).where(Goal.user_id == current_user.id)
        .order_by(desc(Goal.id))
        .limit(1)
        .options(selectinload(Goal.milestones), selectinload(Goal.tasks))
    )
    latest_goal = latest_goal_result.scalars().first()
    
    return {
        "tasks": tasks,
        "habits": habits,
        "finance_balance": total_balance,
        "health_calories": health_calories,
        "active_goals_count": active_goals_count,
        "recent_offers": recent_offers,
        "today_meals": today_meals,
        "recent_expenses": recent_expenses,
        "latest_goal": latest_goal
    }

@router.get("/activity/history", response_model=ActivityHistory)
async def get_activity_history(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get 7-day activity history for the dashboard chart.
    """
    days = []
    
    # Active Goals Count (Current)
    goals_count_result = await db.execute(
        select(func.count(Goal.id)).where(
            Goal.user_id == current_user.id,
            Goal.status == GoalStatus.IN_PROGRESS
        )
    )
    active_goals_count = goals_count_result.scalar() or 0

    for i in range(6, -1, -1):
        day_date = date.today() - timedelta(days=i)
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())
        
        # Finance Stats
        expenses_result = await db.execute(
            select(Expense).where(
                Expense.user_id == current_user.id,
                Expense.timestamp >= day_start,
                Expense.timestamp <= day_end
            )
        )
        expenses = expenses_result.scalars().all()
        balance = sum(e.amount if e.category == ExpenseCategory.INCOME else -e.amount for e in expenses)
        
        # Health Stats
        meals_result = await db.execute(
            select(MealLog).where(
                MealLog.user_id == current_user.id,
                MealLog.created_at >= day_start,
                MealLog.created_at <= day_end
            )
        )
        calories = sum(m.calories or 0.0 for m in meals_result.scalars().all())
        
        days.append(ActivityDay(
            date=day_date.strftime("%d/%m"),
            finance=float(balance),
            health=float(calories),
            goals=int(active_goals_count)
        ))
    
    return ActivityHistory(days=days)

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
    
    print(f"DEBUG: AI raw data: {ai_data}")
    
    # Ensure all required fields exist for OKRAIResponse
    if "title" not in ai_data: ai_data["title"] = input_data.idea[:50]
    if "description" not in ai_data: ai_data["description"] = f"Plan for: {input_data.idea}"
    if "milestones" not in ai_data or not isinstance(ai_data["milestones"], list):
        ai_data["milestones"] = ["Project kickoff", "Execute key steps", "Wrap up"]
    if "tasks" not in ai_data or not isinstance(ai_data["tasks"], list):
        ai_data["tasks"] = ["Define the first step", "Prepare the tools", "Take action!"]

    try:
        okr = OKRAIResponse(**ai_data)
    except Exception as e:
        print(f"DEBUG: Validation error: {e}")
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
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
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
    await db.flush()
    obj_id = goal.id
    await db.commit()
    
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
    # Load data needed for response BEFORE deletion
    result = await db.execute(
        select(Goal)
        .where(Goal.id == goal_id, Goal.user_id == current_user.id)
        .options(
            selectinload(Goal.milestones),
            selectinload(Goal.tasks)
        )
    )
    goal_to_return = result.scalars().first()
    if not goal_to_return:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    await db.delete(goal_to_return)
    await db.commit()
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
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_completed = not task.is_completed
    db.add(task)
    await db.commit()
    await db.refresh(task)
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
    return milestone

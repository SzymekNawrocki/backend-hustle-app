import asyncio
from datetime import datetime, date, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, desc, case, cast, select, Date as SQLDate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import cache, dashboard_key, activity_key, invalidate_dashboard
from app.core.exceptions import AIServiceError
from app.db.pagination import paginate
from app.models.goal import Goal, Milestone, Task, Habit, GoalStatus
from app.models.finance import Expense, ExpenseCategory
from app.models.health import MealLog
from app.models.job_offer import JobOffer
from app.schemas.goal import (
    GoalCreate, GoalResponse, GoalUpdate, DashboardToday,
    SmartCreateInput, TaskResponse, MilestoneResponse,
    ActivityHistory, ActivityDay,
)
from app.schemas.ai import OKRAIResponse
from app.services.ai_service import ai_service


class GoalService:
    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------

    async def create(self, db: AsyncSession, user_id: int, goal_in: GoalCreate) -> Any:
        db_goal = Goal(
            title=goal_in.title,
            description=goal_in.description,
            category=goal_in.category,
            target_date=goal_in.target_date,
            status=goal_in.status,
            user_id=user_id,
        )
        db.add(db_goal)
        await db.flush()
        if goal_in.milestones:
            for m in goal_in.milestones:
                db.add(Milestone(title=m.title, is_completed=m.is_completed, goal_id=db_goal.id))
        await db.commit()
        await invalidate_dashboard(user_id)
        result = await db.execute(
            select(Goal).where(Goal.id == db_goal.id).options(selectinload(Goal.milestones))
        )
        return GoalResponse.model_validate(result.scalars().first()).model_dump()

    async def list(self, db: AsyncSession, user_id: int, page: int, limit: int) -> dict:
        base_filter = (Goal.user_id == user_id, Goal.deleted_at.is_(None))
        return await paginate(
            db,
            query=select(Goal).where(*base_filter).options(
                selectinload(Goal.milestones), selectinload(Goal.tasks)
            ),
            count_query=select(func.count(Goal.id)).where(*base_filter),
            page=page,
            limit=limit,
        )

    async def get(self, db: AsyncSession, user_id: int, goal_id: int) -> Goal:
        result = await db.execute(
            select(Goal)
            .where(Goal.id == goal_id, Goal.user_id == user_id, Goal.deleted_at.is_(None))
            .options(selectinload(Goal.milestones), selectinload(Goal.tasks))
        )
        goal = result.scalars().first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal

    async def update(self, db: AsyncSession, user_id: int, goal_id: int, goal_in: GoalUpdate) -> Any:
        result = await db.execute(
            select(Goal)
            .where(Goal.id == goal_id, Goal.user_id == user_id, Goal.deleted_at.is_(None))
            .options(selectinload(Goal.milestones))
        )
        goal = result.scalars().first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        for field, value in goal_in.model_dump(exclude_unset=True).items():
            setattr(goal, field, value)
        db.add(goal)
        await db.flush()
        obj_id = goal.id
        await db.commit()
        await invalidate_dashboard(user_id)
        result = await db.execute(
            select(Goal).where(Goal.id == obj_id)
            .options(selectinload(Goal.milestones), selectinload(Goal.tasks))
        )
        return GoalResponse.model_validate(result.scalars().first()).model_dump()

    async def delete(self, db: AsyncSession, user_id: int, goal_id: int) -> Goal:
        result = await db.execute(
            select(Goal)
            .where(Goal.id == goal_id, Goal.user_id == user_id, Goal.deleted_at.is_(None))
            .options(selectinload(Goal.milestones), selectinload(Goal.tasks))
        )
        goal = result.scalars().first()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        goal.soft_delete()
        for task in goal.tasks:
            task.soft_delete()
        await db.commit()
        await invalidate_dashboard(user_id)
        return goal

    async def smart_create(self, db: AsyncSession, user_id: int, idea: str) -> Any:
        try:
            ai_data = await ai_service.generate_okr(idea)
        except AIServiceError as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        ai_data.setdefault("title", idea[:50])
        ai_data.setdefault("description", f"Plan for: {idea}")
        if not isinstance(ai_data.get("milestones"), list):
            ai_data["milestones"] = ["Project kickoff", "Execute key steps", "Wrap up"]
        if not isinstance(ai_data.get("tasks"), list):
            ai_data["tasks"] = ["Define the first step", "Prepare the tools", "Take action!"]
        try:
            okr = OKRAIResponse(**ai_data)
        except Exception:
            okr = OKRAIResponse(
                title=ai_data.get("title", "New goal"),
                description=ai_data.get("description", "No description"),
                milestones=ai_data.get("milestones", []),
                tasks=ai_data.get("tasks", []),
            )
        db_goal = Goal(title=okr.title, description=okr.description, user_id=user_id)
        db.add(db_goal)
        await db.flush()
        for m_title in okr.milestones:
            db.add(Milestone(title=m_title, goal_id=db_goal.id))
        for t_title in okr.tasks:
            db.add(Task(title=t_title, goal_id=db_goal.id, user_id=user_id))
        await db.commit()
        result = await db.execute(
            select(Goal).where(Goal.id == db_goal.id)
            .options(selectinload(Goal.milestones), selectinload(Goal.tasks))
        )
        return GoalResponse.model_validate(result.scalars().first()).model_dump()

    # ------------------------------------------------------------------
    # Tasks & Milestones
    # ------------------------------------------------------------------

    async def toggle_task(self, db: AsyncSession, user_id: int, task_id: int) -> Task:
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None))
        )
        task = result.scalars().first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.is_completed = not task.is_completed
        db.add(task)
        await db.commit()
        await db.refresh(task)
        await invalidate_dashboard(user_id)
        return task

    async def toggle_milestone(self, db: AsyncSession, user_id: int, milestone_id: int) -> Milestone:
        result = await db.execute(
            select(Milestone).join(Goal)
            .where(Milestone.id == milestone_id, Goal.user_id == user_id)
        )
        milestone = result.scalars().first()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")
        milestone.is_completed = not milestone.is_completed
        db.add(milestone)
        await db.commit()
        await db.refresh(milestone)
        await invalidate_dashboard(user_id)
        return milestone

    # ------------------------------------------------------------------
    # Dashboard & Activity
    # ------------------------------------------------------------------

    async def get_dashboard(self, db: AsyncSession, user_id: int) -> DashboardToday:
        cached = await cache.get(dashboard_key(user_id))
        if cached is not None:
            return cached
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        (
            tasks_r, habits_r, balance_r, meals_r,
            goals_count_r, offers_r, expenses_r, latest_goal_r,
        ) = await asyncio.gather(
            db.execute(select(Task).where(
                Task.user_id == user_id,
                Task.due_date >= today_start,
                Task.due_date <= today_end,
                Task.deleted_at.is_(None),
            )),
            db.execute(select(Habit).where(Habit.user_id == user_id)),
            db.execute(select(func.sum(
                case((Expense.category == ExpenseCategory.INCOME, Expense.amount), else_=-Expense.amount)
            )).where(Expense.user_id == user_id, Expense.deleted_at.is_(None))),
            db.execute(select(MealLog).where(
                MealLog.user_id == user_id,
                MealLog.created_at >= today_start,
                MealLog.created_at <= today_end,
                MealLog.deleted_at.is_(None),
            )),
            db.execute(select(func.count(Goal.id)).where(
                Goal.user_id == user_id,
                Goal.status == GoalStatus.IN_PROGRESS,
                Goal.deleted_at.is_(None),
            )),
            db.execute(
                select(JobOffer)
                .where(JobOffer.user_id == user_id, JobOffer.deleted_at.is_(None))
                .order_by(desc(JobOffer.id)).limit(5)
            ),
            db.execute(
                select(Expense)
                .where(Expense.user_id == user_id, Expense.deleted_at.is_(None))
                .order_by(desc(Expense.timestamp)).limit(5)
            ),
            db.execute(
                select(Goal)
                .where(Goal.user_id == user_id, Goal.deleted_at.is_(None))
                .order_by(desc(Goal.id)).limit(1)
                .options(selectinload(Goal.milestones), selectinload(Goal.tasks))
            ),
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
        await cache.set(dashboard_key(user_id), dashboard, ttl=30)
        return dashboard

    async def get_activity_history(self, db: AsyncSession, user_id: int) -> ActivityHistory:
        cached = await cache.get(activity_key(user_id))
        if cached is not None:
            return cached
        seven_days_ago = date.today() - timedelta(days=6)
        since = datetime.combine(seven_days_ago, datetime.min.time())
        goals_count_r, finance_rows, health_rows = await asyncio.gather(
            db.execute(select(func.count(Goal.id)).where(
                Goal.user_id == user_id,
                Goal.status == GoalStatus.IN_PROGRESS,
                Goal.deleted_at.is_(None),
            )),
            db.execute(
                select(
                    cast(Expense.timestamp, SQLDate).label("day"),
                    func.sum(case(
                        (Expense.category == ExpenseCategory.INCOME, Expense.amount),
                        else_=-Expense.amount,
                    )).label("balance"),
                )
                .where(Expense.user_id == user_id, Expense.timestamp >= since, Expense.deleted_at.is_(None))
                .group_by(cast(Expense.timestamp, SQLDate))
            ),
            db.execute(
                select(
                    cast(MealLog.created_at, SQLDate).label("day"),
                    func.coalesce(func.sum(MealLog.calories), 0.0).label("calories"),
                )
                .where(MealLog.user_id == user_id, MealLog.created_at >= since, MealLog.deleted_at.is_(None))
                .group_by(cast(MealLog.created_at, SQLDate))
            ),
        )
        active_goals = goals_count_r.scalar() or 0
        finance_map = {row.day: float(row.balance) for row in finance_rows}
        health_map = {row.day: float(row.calories) for row in health_rows}
        days = [
            ActivityDay(
                date=(date.today() - timedelta(days=i)).strftime("%d/%m"),
                finance=finance_map.get(date.today() - timedelta(days=i), 0.0),
                health=health_map.get(date.today() - timedelta(days=i), 0.0),
                goals=active_goals,
            )
            for i in range(6, -1, -1)
        ]
        activity = ActivityHistory(days=days)
        await cache.set(activity_key(user_id), activity, ttl=60)
        return activity


goal_service = GoalService()

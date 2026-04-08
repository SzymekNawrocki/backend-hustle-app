from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from datetime import datetime, timedelta
from app.models.user import User
from app.models.goal import Goal, Milestone, Task, Habit, HabitFrequency, GoalCategory, GoalStatus
from app.models.finance import Expense, ExpenseCategory
from app.models.health import MealLog

async def reset_demo_data(db: AsyncSession, user_id: int):
    # 1. Delete old data
    await db.execute(delete(Milestone).where(Milestone.goal_id.in_(select(Goal.id).where(Goal.user_id == user_id))))
    await db.execute(delete(Task).where(Task.user_id == user_id))
    await db.execute(delete(Habit).where(Habit.user_id == user_id))
    await db.execute(delete(Goal).where(Goal.user_id == user_id))
    await db.execute(delete(Expense).where(Expense.user_id == user_id))
    await db.execute(delete(MealLog).where(MealLog.user_id == user_id))
    
    # 2. Insert fresh demo data
    
    # Habits
    habits = [
        Habit(title="Morning workout", frequency=HabitFrequency.DAILY, streak=15, user_id=user_id),
        Habit(title="10-minute meditation", frequency=HabitFrequency.DAILY, streak=7, user_id=user_id),
        Habit(title="Read a book", frequency=HabitFrequency.DAILY, streak=3, user_id=user_id),
        Habit(title="Weekly planning", frequency=HabitFrequency.WEEKLY, streak=4, user_id=user_id),
    ]
    db.add_all(habits)
    
    # Goals and tasks
    career_goal = Goal(
        title="Promotion to Senior Developer",
        description="Reach senior level by the end of the year",
        category=GoalCategory.CAREER,
        status=GoalStatus.IN_PROGRESS,
        user_id=user_id
    )
    db.add(career_goal)
    await db.flush()  # Get goal ID
    
    milestones = [
        Milestone(title="Master system design", is_completed=True, goal_id=career_goal.id),
        Milestone(title="Lead a project", is_completed=False, goal_id=career_goal.id),
    ]
    db.add_all(milestones)
    
    tasks = [
        Task(title="Auth module code review", is_completed=True, user_id=user_id, goal_id=career_goal.id),
        Task(title="1:1 with manager", is_completed=False, user_id=user_id, due_date=datetime.utcnow() + timedelta(days=1)),
        Task(title="Research Kubernetes (K8s)", is_completed=False, user_id=user_id),
    ]
    db.add_all(tasks)
    
    # Finance
    expenses = [
        Expense(amount=45.50, category=ExpenseCategory.LIFESTYLE, description="Coffee & lunch", user_id=user_id),
        Expense(amount=1200.00, category=ExpenseCategory.OPLATY, description="Rent", user_id=user_id),
        Expense(amount=250.00, category=ExpenseCategory.HUSTLE, description="Online course - Next.js", user_id=user_id),
    ]
    db.add_all(expenses)
    
    # Meals
    meals = [
        MealLog(description="Oatmeal with fruit", calories=450, protein=15, carbs=60, fat=12, user_id=user_id),
        MealLog(description="Chicken with rice and broccoli", calories=650, protein=45, carbs=50, fat=15, user_id=user_id),
    ]
    db.add_all(meals)
    
    await db.commit()

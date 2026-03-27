from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from datetime import datetime, timedelta
from app.models.user import User
from app.models.goal import Goal, Milestone, Task, Habit, HabitFrequency, GoalCategory, GoalStatus
from app.models.finance import Expense, ExpenseCategory
from app.models.health import MealLog

async def reset_demo_data(db: AsyncSession, user_id: int):
    # 1. Usuń stare dane
    await db.execute(delete(Milestone).where(Milestone.goal_id.in_(select(Goal.id).where(Goal.user_id == user_id))))
    await db.execute(delete(Task).where(Task.user_id == user_id))
    await db.execute(delete(Habit).where(Habit.user_id == user_id))
    await db.execute(delete(Goal).where(Goal.user_id == user_id))
    await db.execute(delete(Expense).where(Expense.user_id == user_id))
    await db.execute(delete(MealLog).where(MealLog.user_id == user_id))
    
    # 2. Dodaj nowe przykładowe dane
    
    # Habity
    habits = [
        Habit(title="Poranny trening", frequency=HabitFrequency.DAILY, streak=15, user_id=user_id),
        Habit(title="Medytacja 10 min", frequency=HabitFrequency.DAILY, streak=7, user_id=user_id),
        Habit(title="Czytanie książki", frequency=HabitFrequency.DAILY, streak=3, user_id=user_id),
        Habit(title="Planowanie tygodnia", frequency=HabitFrequency.WEEKLY, streak=4, user_id=user_id),
    ]
    db.add_all(habits)
    
    # Cele i zadania
    career_goal = Goal(
        title="Awans na Senior Developer",
        description="Osiągnięcie poziomu Seniora do końca roku",
        category=GoalCategory.CAREER,
        status=GoalStatus.IN_PROGRESS,
        user_id=user_id
    )
    db.add(career_goal)
    await db.flush() # Aby dostać ID celu
    
    milestones = [
        Milestone(title="Opanowanie system design", is_completed=True, goal_id=career_goal.id),
        Milestone(title="Leadowanie projektu", is_completed=False, goal_id=career_goal.id),
    ]
    db.add_all(milestones)
    
    tasks = [
        Task(title="Przegląd kodu modułu Auth", is_completed=True, user_id=user_id, goal_id=career_goal.id),
        Task(title="Spotkanie 1:1 z managerem", is_completed=False, user_id=user_id, due_date=datetime.utcnow() + timedelta(days=1)),
        Task(title="Zrobić research o K8s", is_completed=False, user_id=user_id),
    ]
    db.add_all(tasks)
    
    # Finanse
    expenses = [
        Expense(amount=45.50, category=ExpenseCategory.LIFESTYLE, description="Kawa i lunch", user_id=user_id),
        Expense(amount=1200.00, category=ExpenseCategory.OPLATY, description="Czynsz", user_id=user_id),
        Expense(amount=250.00, category=ExpenseCategory.HUSTLE, description="Kurs online - Next.js", user_id=user_id),
    ]
    db.add_all(expenses)
    
    # Posiłki
    meals = [
        MealLog(description="Owsianka z owocami", calories=450, protein=15, carbs=60, fat=12, user_id=user_id),
        MealLog(description="Kurczak z ryżem i brokułami", calories=650, protein=45, carbs=50, fat=15, user_id=user_id),
    ]
    db.add_all(meals)
    
    await db.commit()

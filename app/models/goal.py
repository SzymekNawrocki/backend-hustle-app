import enum
from datetime import date, datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, ForeignKey, Date, DateTime, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User
from app.db.types import NaiveDateTime

class GoalCategory(str, enum.Enum):
    CAREER = "CAREER"
    FINANCE = "FINANCE"
    HEALTH = "HEALTH"
    PERSONAL = "PERSONAL"

class GoalStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

class Goal(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[GoalCategory] = mapped_column(Enum(GoalCategory), default=GoalCategory.PERSONAL)
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[GoalStatus] = mapped_column(Enum(GoalStatus), default=GoalStatus.IN_PROGRESS)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="goals")
    
    milestones: Mapped[List["Milestone"]] = relationship(
        "Milestone", back_populates="goal", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="goal")

class Milestone(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    goal_id: Mapped[int] = mapped_column(Integer, ForeignKey("goal.id"), nullable=False)
    goal: Mapped["Goal"] = relationship("Goal", back_populates="milestones")

class Task(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(NaiveDateTime, nullable=True)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="tasks")
    
    goal_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("goal.id"), nullable=True)
    goal: Mapped[Optional["Goal"]] = relationship("Goal", back_populates="tasks")

class HabitFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"

class Habit(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)
    frequency: Mapped[HabitFrequency] = mapped_column(Enum(HabitFrequency), default=HabitFrequency.DAILY)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="habits")

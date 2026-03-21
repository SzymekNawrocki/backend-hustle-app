from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, computed_field
from app.models.goal import GoalCategory, GoalStatus, HabitFrequency

# Milestone Schemas
class MilestoneBase(BaseModel):
    title: str
    is_completed: bool = False

class MilestoneCreate(MilestoneBase):
    pass

class MilestoneResponse(MilestoneBase):
    id: int
    goal_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_completed: bool = False
    due_date: Optional[datetime] = None
    goal_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Habit Schemas
class HabitBase(BaseModel):
    title: str
    frequency: HabitFrequency = HabitFrequency.DAILY

class HabitCreate(HabitBase):
    pass

class HabitResponse(HabitBase):
    id: int
    streak: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Goal Schemas
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: GoalCategory = GoalCategory.PERSONAL
    target_date: Optional[date] = None
    status: GoalStatus = GoalStatus.IN_PROGRESS

class GoalCreate(GoalBase):
    milestones: Optional[List[MilestoneCreate]] = None

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[GoalCategory] = None
    target_date: Optional[date] = None
    status: Optional[GoalStatus] = None

class GoalResponse(GoalBase):
    id: int
    user_id: int
    milestones: List[MilestoneResponse] = []
    tasks: List[TaskResponse] = []
    
    @computed_field
    @property
    def progress_percentage(self) -> float:
        if not self.milestones:
            return 0.0
        completed = sum(1 for m in self.milestones if m.is_completed)
        return round((completed / len(self.milestones)) * 100, 2)
    
    model_config = ConfigDict(from_attributes=True)

# Dashboard Schema
class DashboardToday(BaseModel):
    tasks: List[TaskResponse]
    habits: List[HabitResponse]
    finance_balance: float = 0.0
    health_calories: float = 0.0
    active_goals_count: int = 0

# Smart Create Schema
class SmartCreateInput(BaseModel):
    idea: str

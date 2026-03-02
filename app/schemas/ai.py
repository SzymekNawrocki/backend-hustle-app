from typing import List, Optional
from pydantic import BaseModel

class MealAIResponse(BaseModel):
    calories: int
    protein: float
    carbs: float
    fat: float

class OKRAIResponse(BaseModel):
    title: str
    description: str
    milestones: List[str]
    tasks: List[str]

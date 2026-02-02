from typing import List, Optional
from pydantic import BaseModel

class MealAIResponse(BaseModel):
    calories: int
    protein: float
    carbs: float
    fat: float

class JobAnalysisAIResponse(BaseModel):
    match_score: int
    matching_keywords: List[str]
    missing_skills: List[str]

class OKRAIResponse(BaseModel):
    title: str
    milestones: List[str]

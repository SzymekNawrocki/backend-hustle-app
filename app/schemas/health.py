from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class MealLogBase(BaseModel):
    description: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None

class MealLogCreate(MealLogBase):
    pass

class MealLogResponse(MealLogBase):
    id: int
    user_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MealLogAIRequest(BaseModel):
    text: str

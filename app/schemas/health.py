from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

class MealLogBase(BaseModel):
    description: str
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    created_at: Optional[datetime] = None

    @field_validator("created_at", mode="after")
    @classmethod
    def set_created_at(cls, v):
        if v is None:
            return datetime.now(timezone.utc).replace(tzinfo=None)
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

class MealLogCreate(MealLogBase):
    pass

class MealLogResponse(MealLogBase):
    id: int
    user_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MealLogAIRequest(BaseModel):
    text: str

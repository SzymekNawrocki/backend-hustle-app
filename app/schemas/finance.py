from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

# Expense Schemas
class ExpenseBase(BaseModel):
    amount: float
    category: str
    description: str
    timestamp: Optional[datetime] = None

    @field_validator("timestamp", mode="after")
    @classmethod
    def set_timestamp(cls, v):
        if v is None:
            return datetime.now(timezone.utc).replace(tzinfo=None)
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

class ExpenseCreate(ExpenseBase):
    pass

class ExpenseResponse(ExpenseBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

class HustleInputRequest(BaseModel):
    text: str
    forced_category: Optional[str] = None

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator
from app.models.finance import ExpenseCategory

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

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = None
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("timestamp", mode="after")
    @classmethod
    def strip_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v


class HustleInputRequest(BaseModel):
    text: str
    forced_category: Optional[str] = None

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HustleItemCreate(BaseModel):
    title: str
    category: str
    value: float

class HustleItemResponse(HustleItemCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
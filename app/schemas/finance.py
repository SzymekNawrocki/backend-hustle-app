from pydantic import BaseModel, ConfigDict, computed_field
from datetime import datetime
from typing import Optional
from app.models.finance import AssetType

class AssetBase(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType
    amount: float
    buy_price: float
    current_price: Optional[float] = None

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    created_at: datetime

    @computed_field
    @property
    def total_invested(self) -> float:
        return self.amount * self.buy_price

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, computed_field, field_validator
from app.models.finance import AssetType, TransactionType

# Transaction Schemas
class TransactionBase(BaseModel):
    type: TransactionType
    amount: float
    price_per_unit: float
    fee: float = 0.0
    timestamp: Optional[datetime] = None

    @field_validator("timestamp", mode="after")
    @classmethod
    def set_timestamp(cls, v):
        if v is None:
            return datetime.now(timezone.utc).replace(tzinfo=None)
        if v.tzinfo is not None:
            return v.replace(tzinfo=None)
        return v

class TransactionCreate(TransactionBase):
    asset_id: int

class TransactionResponse(TransactionBase):
    id: int
    asset_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Asset Schemas
class AssetBase(BaseModel):
    ticker: str
    name: str
    asset_type: AssetType = AssetType.CASH

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Portfolio Schemas
class AssetPortfolioResponse(AssetResponse):
    transactions: List[TransactionResponse] = []
    
    @computed_field
    @property
    def total_quantity(self) -> float:
        buys = sum(t.amount for t in self.transactions if t.type == TransactionType.BUY)
        sells = sum(t.amount for t in self.transactions if t.type == TransactionType.SELL)
        return round(buys - sells, 8)
    
    @computed_field
    @property
    def total_invested(self) -> float:
        return round(sum(t.amount * t.price_per_unit + t.fee for t in self.transactions if t.type == TransactionType.BUY), 2)
    
    @computed_field
    @property
    def average_buy_price(self) -> float:
        total_qty_bought = sum(t.amount for t in self.transactions if t.type == TransactionType.BUY)
        if total_qty_bought == 0:
            return 0.0
        total_cost = sum(t.amount * t.price_per_unit for t in self.transactions if t.type == TransactionType.BUY)
        return round(total_cost / total_qty_bought, 4)
    
    model_config = ConfigDict(from_attributes=True)

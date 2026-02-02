import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Float, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class AssetType(str, enum.Enum):
    CRYPTO = "CRYPTO"
    STOCK = "STOCK"
    CASH = "CASH"

class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Asset(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), default=AssetType.CASH)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="assets")
    
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="asset", cascade="all, delete-orphan"
    )

class Transaction(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("asset.id"), nullable=False)
    asset: Mapped["Asset"] = relationship("Asset", back_populates="transactions")

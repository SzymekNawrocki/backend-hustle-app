from sqlalchemy import Column, Integer, String, Float, Enum, DateTime
from sqlalchemy.sql import func
import enum
from app.database import Base

class AssetType(enum.Enum):
    Crypto = "Crypto"
    Stock = "Stock"
    Cash = "Cash"
    RealEstate = "RealEstate"

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    amount = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

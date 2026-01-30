from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.database import Base

class HustleItem(Base):
    __tablename__ = "hustle_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    category = Column(String)
    value = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
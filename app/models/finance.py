import enum
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Float, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User
from app.db.types import NaiveDateTime

class ExpenseCategory(str, enum.Enum):
    OPLATY = "OPLATY"
    HUSTLE = "HUSTLE"
    LIFESTYLE = "LIFESTYLE"
    INCOME = "INCOME"

class Expense(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(Enum(ExpenseCategory), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(NaiveDateTime, default=datetime.utcnow)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="expenses")

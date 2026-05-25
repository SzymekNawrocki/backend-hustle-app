import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.db.mixins import SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
from app.db.types import NaiveDateTime

class ExpenseCategory(str, enum.Enum):
    EXPENSES = "EXPENSES"
    HUSTLE = "HUSTLE"
    LIFESTYLE = "LIFESTYLE"
    INCOME = "INCOME"

class Expense(SoftDeleteMixin, Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(Enum(ExpenseCategory), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(NaiveDateTime, default=datetime.utcnow, index=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    user: Mapped["User"] = relationship("User", back_populates="expenses")

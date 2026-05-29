import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.types import NaiveDateTime


class DonationStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class Donation(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stripe_session_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    supporter_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    supporter_email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus), nullable=False, default=DonationStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(NaiveDateTime, default=datetime.utcnow, index=True)

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.types import NaiveDateTime


class PasswordResetToken(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(NaiveDateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(NaiveDateTime, nullable=True, default=None)

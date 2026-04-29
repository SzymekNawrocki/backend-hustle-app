from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from app.db.types import NaiveDateTime


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(NaiveDateTime, nullable=True, default=None)

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)

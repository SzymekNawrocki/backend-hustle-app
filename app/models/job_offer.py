import enum
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User


class OfferStatus(str, enum.Enum):
    Wyslano = "wysłano"
    Etap1 = "1 etap"
    Etap2 = "2 etap"
    Etap3 = "3 etap"
    Umowa = "umowa"


class JobOffer(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    company: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[OfferStatus] = mapped_column(
        ENUM(
            OfferStatus,
            name="offerstatus",
            create_type=False,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="job_offers")

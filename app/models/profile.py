from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class UserProfile(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cv_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    skills: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    user: Mapped["User"] = relationship("User", back_populates="profile")

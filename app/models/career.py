import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class JobStatus(str, enum.Enum):
    TO_APPLY = "TO_APPLY"
    APPLIED = "APPLIED"
    INTERVIEWING = "INTERVIEWING"
    OFFER = "OFFER"
    REJECTED = "REJECTED"

class InterviewType(str, enum.Enum):
    HR = "HR"
    TECH = "TECH"
    FINAL = "FINAL"

class JobApplication(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String, index=True, nullable=False)
    position: Mapped[str] = mapped_column(String, index=True, nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.TO_APPLY)
    listing_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description_raw: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="applications")
    
    interviews: Mapped[List["Interview"]] = relationship(
        "Interview", back_populates="application", cascade="all, delete-orphan"
    )

class Interview(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type: Mapped[InterviewType] = mapped_column(Enum(InterviewType), default=InterviewType.TECH)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_application.id"), nullable=False)
    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="interviews")

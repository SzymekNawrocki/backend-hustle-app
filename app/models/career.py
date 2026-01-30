from sqlalchemy import Column, Integer, String, Enum, Text, DateTime, JSON
from sqlalchemy.sql import func
import enum
from app.database import Base

class JobStatus(enum.Enum):
    Applied = "Applied"
    Interview = "Interview"
    Offer = "Offer"
    Rejected = "Rejected"

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.Applied)
    listing_url = Column(String, nullable=True)
    description_raw = Column(Text, nullable=True)
    ai_keywords = Column(JSON, nullable=True)
    match_score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

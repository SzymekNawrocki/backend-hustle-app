from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from app.models.career import JobStatus

class JobApplicationBase(BaseModel):
    company: str
    position: str
    status: JobStatus = JobStatus.Applied
    listing_url: Optional[str] = None
    description_raw: Optional[str] = None

class JobApplicationCreate(JobApplicationBase):
    pass

class JobApplicationResponse(JobApplicationBase):
    id: int
    ai_keywords: Optional[List[str]] = None
    match_score: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.career import JobStatus, InterviewType

# --- NOWE: Schematy Profilu ---
class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    cv_text: Optional[str] = None
    job_title: Optional[str] = None

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

# --- Interview Schemas ---
class InterviewBase(BaseModel):
    date: datetime
    type: InterviewType = InterviewType.TECH
    notes: Optional[str] = None

class InterviewCreate(InterviewBase):
    application_id: int

class InterviewResponse(InterviewBase):
    id: int
    application_id: int
    
    model_config = ConfigDict(from_attributes=True)

# --- Job Application Schemas ---
class JobApplicationBase(BaseModel):
    company: str
    position: str
    status: JobStatus = JobStatus.TO_APPLY
    listing_url: Optional[str] = None
    description_raw: Optional[str] = None
    match_score: Optional[float] = None

class JobApplicationCreate(JobApplicationBase):
    pass

class JobApplicationResponse(JobApplicationBase):
    id: int
    user_id: int
    interviews: List[InterviewResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

# --- Analysis Schemas ---
class JobDescriptionRequest(BaseModel):
    description: str

class CareerAnalysisResponse(BaseModel):
    match_score: float
    pros: List[str]
    cons: List[str]
    missing_skills: List[str]
    summary: str
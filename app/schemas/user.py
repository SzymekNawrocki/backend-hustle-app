from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any

class SkillSchema(BaseModel):
    name: str
    level: int  # 1-10

class UserProfileBase(BaseModel):
    full_name: str
    job_title: Optional[str] = None
    bio: Optional[str] = None
    experience_years: int = 0
    skills: List[SkillSchema] = []

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    bio: Optional[str] = None
    experience_years: Optional[int] = None
    skills: Optional[List[SkillSchema]] = None

class UserProfileResponse(UserProfileBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

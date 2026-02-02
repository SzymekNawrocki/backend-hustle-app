from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    cv_text: Optional[str] = None
    job_title: Optional[str] = None
    skills: Optional[List[str]] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)

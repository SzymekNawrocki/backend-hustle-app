from typing import Optional
from pydantic import BaseModel, ConfigDict, HttpUrl

from app.models.job_offer import OfferStatus


class JobOfferBase(BaseModel):
    title: str
    company: Optional[str] = None
    status: OfferStatus
    url: str
    notes: Optional[str] = None


class JobOfferCreate(JobOfferBase):
    pass


class JobOfferUpdate(BaseModel):
    company: Optional[str] = None
    status: Optional[OfferStatus] = None
    notes: Optional[str] = None


class JobOfferResponse(JobOfferBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

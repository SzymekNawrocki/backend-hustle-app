from typing import Optional
from pydantic import BaseModel, ConfigDict, HttpUrl

from app.models.job_offer import OfferStatus


class JobOfferBase(BaseModel):
    title: str
    status: OfferStatus
    url: str


class JobOfferCreate(JobOfferBase):
    pass


class JobOfferResponse(JobOfferBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

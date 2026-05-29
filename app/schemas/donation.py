from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.donation import DonationStatus


class CreateCheckoutRequest(BaseModel):
    amount_cents: int = Field(ge=100, le=10000)
    supporter_name: Optional[str] = Field(None, max_length=100)


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class DonationResponse(BaseModel):
    id: int
    amount_cents: int
    currency: str
    supporter_name: Optional[str]
    status: DonationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.donation import (
    CheckoutSessionResponse,
    CreateCheckoutRequest,
    DonationResponse,
)
from app.services.donation_service import donation_service

router = APIRouter()


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
@limiter.limit("5/hour")
async def create_checkout_session(
    request: Request,
    checkout_in: CreateCheckoutRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    # Stripe uses {CHECKOUT_SESSION_ID} as a literal placeholder — double braces escape in f-string
    success_url = f"{settings.FRONTEND_URL}/support/thanks?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.FRONTEND_URL}/support"
    checkout_url = await donation_service.create_checkout_session(
        db,
        amount_cents=checkout_in.amount_cents,
        supporter_name=checkout_in.supporter_name,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return {"checkout_url": checkout_url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    await donation_service.handle_webhook(db, payload, sig)
    return {"status": "ok"}


@router.get("/recent", response_model=list[DonationResponse])
async def get_recent_donations(
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    return await donation_service.get_recent(db)

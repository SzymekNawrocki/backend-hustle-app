import asyncio
from typing import Optional

import stripe
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DomainError
from app.models.donation import Donation, DonationStatus


class DonationService:

    async def create_checkout_session(
        self,
        db: AsyncSession,
        amount_cents: int,
        supporter_name: Optional[str],
        success_url: str,
        cancel_url: str,
    ) -> str:
        if not settings.STRIPE_SECRET_KEY:
            raise DomainError("Payments are not configured yet", 503)

        def _create() -> stripe.checkout.Session:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            return stripe.checkout.Session.create(
                payment_method_types=["card"],
                mode="payment",
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": "Support Hustle App",
                                "description": "One-time donation — thank you!",
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=cancel_url,
            )

        session = await asyncio.to_thread(_create)

        donation = Donation(
            stripe_session_id=session.id,
            amount_cents=amount_cents,
            currency="usd",
            supporter_name=supporter_name,
            status=DonationStatus.PENDING,
        )
        db.add(donation)
        await db.commit()

        return session.url  # type: ignore[return-value]

    async def handle_webhook(
        self,
        db: AsyncSession,
        payload: bytes,
        sig_header: str,
    ) -> Optional[tuple[str, int]]:
        """Process Stripe webhook. Returns (supporter_email, amount_cents) if a
        donation completed with a known email, otherwise None."""
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise DomainError("Webhook secret not configured", 500)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.SignatureVerificationError:
            raise DomainError("Invalid webhook signature", 400)
        except ValueError:
            raise DomainError("Invalid payload", 400)

        if event["type"] == "checkout.session.completed":
            session_obj = event["data"]["object"]
            stripe_session_id: str = session_obj["id"]
            customer_details = session_obj.get("customer_details") or {}
            supporter_email: Optional[str] = customer_details.get("email")

            result = await db.execute(
                select(Donation).where(Donation.stripe_session_id == stripe_session_id)
            )
            donation = result.scalars().first()
            if donation:
                donation.status = DonationStatus.COMPLETED
                if supporter_email:
                    donation.supporter_email = supporter_email
                await db.commit()
                if supporter_email:
                    return supporter_email, donation.amount_cents
        return None

    async def get_recent(self, db: AsyncSession, limit: int = 10) -> list[Donation]:
        result = await db.execute(
            select(Donation)
            .where(Donation.status == DonationStatus.COMPLETED)
            .order_by(desc(Donation.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


donation_service = DonationService()

"""Arq task functions — imported by WorkerSettings and enqueued by endpoints."""

from typing import Any


async def send_reset_email(ctx: dict[str, Any], to_email: str, reset_token: str) -> None:
    from app.services.email_service import email_service
    await email_service.send_password_reset(to_email, reset_token)


async def send_donation_thanks(ctx: dict[str, Any], to_email: str, amount_cents: int) -> None:
    from app.services.email_service import email_service
    await email_service.send_donation_thanks(to_email, amount_cents)

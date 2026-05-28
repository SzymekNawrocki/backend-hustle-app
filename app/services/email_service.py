import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import EmailServiceError

_TEMPLATE_DIR = Path(__file__).parent / "email_templates"


def _load_template(name: str) -> str:
    return (_TEMPLATE_DIR / name).read_text(encoding="utf-8")


def _send_sync(params: dict) -> None:
    """Synchronous Resend call — run inside asyncio.to_thread."""
    import resend  # lazy import so the app starts without RESEND_API_KEY in dev

    resend.api_key = settings.RESEND_API_KEY  # type: ignore[assignment]
    resend.Emails.send(params)  # type: ignore[attr-defined]


class EmailService:
    async def send_password_reset(self, to_email: str, reset_token: str) -> None:
        if not settings.RESEND_API_KEY:
            # Dev mode: log the reset URL to stdout instead of sending
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
            print(f"[DEV] Password reset URL for {to_email}: {reset_url}", flush=True)
            return

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        year = datetime.now(timezone.utc).year
        html = (
            _load_template("reset_password.html")
            .replace("{reset_url}", reset_url)
            .replace("{year}", str(year))
        )

        params = {
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": "Reset your Hustle App password",
            "html": html,
        }

        try:
            await asyncio.to_thread(_send_sync, params)
        except Exception as exc:
            raise EmailServiceError(f"Failed to send password reset email: {exc}") from exc


email_service = EmailService()

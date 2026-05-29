"""Arq worker entry point.

Run with:
    python -m arq app.workers.worker.WorkerSettings
"""

from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import send_reset_email, send_donation_thanks


class WorkerSettings:
    functions = [send_reset_email, send_donation_thanks]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL or "redis://localhost:6379")
    max_jobs = 10
    job_timeout = 60

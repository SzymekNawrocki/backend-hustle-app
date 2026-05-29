import json
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.limiter import limiter

def _sentry_before_send(event: dict, hint: dict) -> dict:
    """Strip cookies and auth headers from every Sentry event to avoid PII leaks."""
    req = event.get("request", {})
    req.pop("cookies", None)
    headers = req.get("headers", {})
    headers.pop("Authorization", None)
    headers.pop("authorization", None)
    headers.pop("Cookie", None)
    headers.pop("cookie", None)
    return event


if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
        environment="production",
        before_send=_sentry_before_send,
    )


# ---------------------------------------------------------------------------
# Structured logging helpers
# ---------------------------------------------------------------------------

def _log(record: dict) -> None:
    """Write a single JSON log line to stdout (Render collects stdout)."""
    print(json.dumps(record, default=str), flush=True, file=sys.stdout)


def _extract_token(request: Request) -> str | None:
    """Extract raw JWT from Authorization header or cookie."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return request.cookies.get(settings.AUTH_COOKIE_NAME) or None


def _decode_user_id(token: str) -> int | None:
    """Decode JWT and return user_id, or None on any error."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (JWTError, ValueError):
        return None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from app.workers.pool import get_arq_pool, close_arq_pool
    await get_arq_pool()  # pre-warm if REDIS_URL is set
    yield
    await close_arq_pool()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    token = _extract_token(request)
    request.state.token = token
    request.state.user_id = _decode_user_id(token) if token else None

    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    _log({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "response_time_ms": elapsed_ms,
        "user_id": request.state.user_id,
    })

    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    _log({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(request.state, "request_id", None),
        "level": "warning",
        "event": "rate_limit_exceeded",
        "detail": exc.detail,
        "path": request.url.path,
        "user_id": getattr(request.state, "user_id", None),
    })
    return JSONResponse(
        status_code=429,
        content={"detail": f"Za dużo requestów. Limit: {exc.detail}. Poczekaj chwilę i spróbuj ponownie."},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        _log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": getattr(request.state, "request_id", None),
            "level": "error",
            "event": "http_exception",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "user_id": getattr(request.state, "user_id", None),
        })
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    sentry_sdk.capture_exception(exc)
    _log({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(request.state, "request_id", None),
        "level": "critical",
        "event": "unhandled_exception",
        "exception_type": type(exc).__name__,
        "detail": str(exc),
        "path": request.url.path,
        "method": request.method,
        "user_id": getattr(request.state, "user_id", None),
    })
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Root endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def read_root():
    return {"status": "success", "message": f"{settings.PROJECT_NAME} API is running!"}


@app.get("/health-check")
async def health_check():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.user import User

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(User).limit(1))
        return {"status": "ok", "database": "connected", "version": settings.VERSION}
    except Exception as e:
        return {"status": "error", "database": str(e), "version": settings.VERSION}

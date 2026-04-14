import json
import sys
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from slowapi.errors import RateLimitExceeded

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.limiter import limiter


# ---------------------------------------------------------------------------
# Structured logging helpers
# ---------------------------------------------------------------------------

def _log(record: dict) -> None:
    """Write a single JSON log line to stdout (Render collects stdout)."""
    print(json.dumps(record, default=str), flush=True, file=sys.stdout)


def _extract_user_id(request: Request) -> int | None:
    """Decode JWT from Authorization header or cookie; return user_id or None."""
    token: str | None = None
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            sub = payload.get("sub")
            return int(sub) if sub is not None else None
        except (JWTError, ValueError):
            pass
    return None


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.state.limiter = limiter


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.user_id = _extract_user_id(request)

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

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.db.base import Base
from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Custom middleware to log origin for debugging
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin:
        print(f"DEBUG: origin={origin} path={request.url.path}")
    response = await call_next(request)
    return response

# Handle Faraday/CORS/Auth errors specifically
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    print(f"DEBUG: HTTPException: status={exc.status_code} detail={exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={"Access-Control-Allow-Origin": "*"} # Ensure preflight/errors always have CORS
    )

# Global Exception Handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"DEBUG: Global Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal Server Error: {str(exc)}",
            "type": str(type(exc).__name__),
            "path": request.url.path,
            "method": request.method
        },
        headers={"Access-Control-Allow-Origin": "*"} # Force CORS for error responses
    )


# CORS Configuration
# specific origins are required when allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

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
        return {"status": "ok", "database": "connected", "version": "V4_SHA256_DEBUG"}
    except Exception as e:
        return {"status": "error", "database": str(e), "version": "V4_SHA256_DEBUG"}

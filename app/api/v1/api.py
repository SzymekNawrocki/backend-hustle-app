from fastapi import APIRouter
from app.api.v1.endpoints import auth, goals, finance, health

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(health.router, prefix="/health", tags=["health"])

from typing import Any
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.health import MealLogAIRequest, MealLogResponse
from app.schemas.pagination import PaginatedResponse
from app.services.health_service import health_service

router = APIRouter()


@router.post("/log-meal-ai", response_model=MealLogResponse)
@limiter.limit("10/minute")
async def log_meal_ai(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    input_data: MealLogAIRequest = ...,
) -> Any:
    return await health_service.log_from_text(db, current_user.id, input_data)


@router.delete("/meals/{meal_id}", response_model=MealLogResponse)
async def delete_meal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    meal_id: int,
) -> Any:
    return await health_service.delete(db, current_user.id, meal_id)


@router.get("/meals", response_model=PaginatedResponse[MealLogResponse])
async def read_meals(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    return await health_service.list(db, current_user.id, page, limit)

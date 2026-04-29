from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api import deps
from app.core.exceptions import AIServiceError
from app.core.limiter import limiter
from app.core.cache import invalidate_dashboard
from app.db.pagination import paginate
from app.models.user import User
from app.models.health import MealLog
from app.schemas.health import MealLogResponse, MealLogAIRequest
from app.schemas.pagination import PaginatedResponse
from app.schemas.ai import MealAIResponse
from app.services.ai_service import ai_service

router = APIRouter()

@router.post("/log-meal-ai", response_model=MealLogResponse)
@limiter.limit("10/minute")
async def log_meal_ai(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    input_data: MealLogAIRequest = ...,
) -> Any:
    """
    Log a meal using natural language via AI analysis.
    """
    try:
        ai_data = await ai_service.parse_meal(input_data.text)
        nutrition = MealAIResponse(**ai_data)
    except AIServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid AI output: {e}")

    db_obj = MealLog(
        description=input_data.text,
        calories=nutrition.calories,
        protein=nutrition.protein,
        carbs=nutrition.carbs,
        fat=nutrition.fat,
        user_id=current_user.id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    await invalidate_dashboard(current_user.id)
    return db_obj


@router.delete("/meals/{meal_id}", response_model=MealLogResponse)
async def delete_meal(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    meal_id: int
) -> Any:
    result = await db.execute(
        select(MealLog).where(
            MealLog.id == meal_id,
            MealLog.user_id == current_user.id,
            MealLog.deleted_at.is_(None),
        )
    )
    meal = result.scalars().first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    meal.soft_delete()
    await db.commit()
    await invalidate_dashboard(current_user.id)
    return meal

@router.get("/meals", response_model=PaginatedResponse[MealLogResponse])
async def read_meals(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    base_filter = (MealLog.user_id == current_user.id, MealLog.deleted_at.is_(None))
    return await paginate(
        db,
        query=select(MealLog).where(*base_filter).order_by(MealLog.id.desc()),
        count_query=select(func.count(MealLog.id)).where(*base_filter),
        page=page,
        limit=limit,
    )

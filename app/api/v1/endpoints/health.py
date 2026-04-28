from datetime import datetime, timezone
from math import ceil
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api import deps
from app.core.limiter import limiter
from app.core.cache import invalidate_dashboard
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
    ai_data = await ai_service.parse_meal(input_data.text)
    
    if "error" in ai_data:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ai_data.get("details", "AI Analysis failed")
        )
    
    # Validate with Pydantic
    try:
        nutrition = MealAIResponse(**ai_data)
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

    meal.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
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
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count(MealLog.id)).where(
            MealLog.user_id == current_user.id,
            MealLog.deleted_at.is_(None),
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(MealLog)
        .where(MealLog.user_id == current_user.id, MealLog.deleted_at.is_(None))
        .order_by(MealLog.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return {
        "items": result.scalars().all(),
        "total": total,
        "page": page,
        "pages": ceil(total / limit) if total > 0 else 1,
    }

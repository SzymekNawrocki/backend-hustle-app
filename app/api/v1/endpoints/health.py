from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.models.user import User
from app.models.health import MealLog
from app.schemas.health import MealLogResponse, MealLogAIRequest
from app.schemas.ai import MealAIResponse
from app.services.ai_service import ai_service

router = APIRouter()

@router.post("/log-meal-ai", response_model=MealLogResponse)
async def log_meal_ai(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    input_data: MealLogAIRequest
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
            MealLog.user_id == current_user.id
        )
    )
    meal = result.scalars().first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    await db.delete(meal)
    await db.commit()
    return meal

@router.get("/meals", response_model=List[MealLogResponse])
async def read_meals(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve meal logs for current user.
    """
    result = await db.execute(
        select(MealLog)
        .where(MealLog.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_dashboard
from app.core.exceptions import AIServiceError, NotFoundError
from app.db.pagination import paginate
from app.models.health import MealLog
from app.schemas.ai import MealAIResponse
from app.schemas.health import MealLogAIRequest
from app.services.ai_service import ai_service


class HealthService:

    async def list(self, db: AsyncSession, user_id: int, page: int, limit: int) -> dict:
        base_filter = (MealLog.user_id == user_id, MealLog.deleted_at.is_(None))
        return await paginate(
            db,
            query=select(MealLog).where(*base_filter).order_by(MealLog.id.desc()),
            count_query=select(func.count(MealLog.id)).where(*base_filter),
            page=page,
            limit=limit,
        )

    async def log_from_text(
        self, db: AsyncSession, user_id: int, input_data: MealLogAIRequest
    ) -> MealLog:
        ai_data = await ai_service.parse_meal(input_data.text)
        try:
            nutrition = MealAIResponse(**ai_data)
        except Exception as exc:
            raise AIServiceError("AI returned invalid meal data") from exc

        db_obj = MealLog(
            description=input_data.text,
            calories=nutrition.calories,
            protein=nutrition.protein,
            carbs=nutrition.carbs,
            fat=nutrition.fat,
            user_id=user_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await invalidate_dashboard(user_id)
        return db_obj

    async def delete(self, db: AsyncSession, user_id: int, meal_id: int) -> MealLog:
        result = await db.execute(
            select(MealLog).where(
                MealLog.id == meal_id,
                MealLog.user_id == user_id,
                MealLog.deleted_at.is_(None),
            )
        )
        meal = result.scalars().first()
        if not meal:
            raise NotFoundError("Meal not found")

        meal.soft_delete()
        await db.commit()
        await invalidate_dashboard(user_id)
        return meal


health_service = HealthService()

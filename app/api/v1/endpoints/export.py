import csv
import io
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.finance import Expense
from app.models.health import MealLog
from app.models.user import User

router = APIRouter()


@router.get("/expenses.csv")
async def export_expenses(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    result = await db.execute(
        select(Expense)
        .where(Expense.user_id == current_user.id, Expense.deleted_at.is_(None))
        .order_by(Expense.timestamp.desc())
    )
    expenses = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "date", "amount", "category", "description"])
    for e in expenses:
        writer.writerow([
            e.id,
            e.timestamp.strftime("%Y-%m-%d %H:%M") if e.timestamp else "",
            e.amount,
            e.category.value if hasattr(e.category, "value") else e.category,
            e.description,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )


@router.get("/meals.csv")
async def export_meals(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    result = await db.execute(
        select(MealLog)
        .where(MealLog.user_id == current_user.id, MealLog.deleted_at.is_(None))
        .order_by(MealLog.created_at.desc())
    )
    meals = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "date", "description", "calories", "protein", "carbs", "fat"])
    for m in meals:
        writer.writerow([
            m.id,
            m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
            m.description,
            m.calories or "",
            m.protein or "",
            m.carbs or "",
            m.fat or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=meals.csv"},
    )

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_dashboard
from app.core.exceptions import AIServiceError, NotFoundError
from app.db.pagination import paginate
from app.models.finance import Expense
from app.schemas.finance import ExpenseUpdate, HustleInputRequest
from app.services.ai_service import ai_service


class FinanceService:

    async def list(self, db: AsyncSession, user_id: int, page: int, limit: int) -> dict:
        base_filter = (Expense.user_id == user_id, Expense.deleted_at.is_(None))
        return await paginate(
            db,
            query=select(Expense).where(*base_filter).order_by(Expense.timestamp.desc()),
            count_query=select(func.count(Expense.id)).where(*base_filter),
            page=page,
            limit=limit,
        )

    async def update(
        self, db: AsyncSession, user_id: int, expense_id: int, expense_in: ExpenseUpdate
    ) -> Expense:
        result = await db.execute(
            select(Expense).where(
                Expense.id == expense_id,
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
            )
        )
        expense = result.scalars().first()
        if not expense:
            raise NotFoundError("Expense not found")

        for field, value in expense_in.model_dump(exclude_unset=True).items():
            setattr(expense, field, value)

        await db.commit()
        await db.refresh(expense)
        await invalidate_dashboard(user_id)
        return expense

    async def delete(self, db: AsyncSession, user_id: int, expense_id: int) -> Expense:
        result = await db.execute(
            select(Expense).where(
                Expense.id == expense_id,
                Expense.user_id == user_id,
                Expense.deleted_at.is_(None),
            )
        )
        expense = result.scalars().first()
        if not expense:
            raise NotFoundError("Expense not found")

        expense.soft_delete()
        await db.commit()
        await invalidate_dashboard(user_id)
        return expense

    async def create_from_text(
        self, db: AsyncSession, user_id: int, hustle_in: HustleInputRequest
    ) -> Any:
        parsed_data = await ai_service.parse_hustle_input(hustle_in.text)

        amount = parsed_data.get("amount")
        category = hustle_in.forced_category or parsed_data.get("category")
        description = parsed_data.get("description")

        if amount is None:
            raise AIServiceError(
                "Couldn't find the amount in your text. Example: '50 PLN for pizza'",
                status_code=400,
            )
        if category is None or description is None:
            raise AIServiceError("AI couldn't categorize the expense reliably.", status_code=400)

        db_obj = Expense(
            amount=float(amount),
            category=category.upper(),
            description=description,
            user_id=user_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await invalidate_dashboard(user_id)
        return db_obj


finance_service = FinanceService()

from typing import Any
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.finance import ExpenseResponse, ExpenseUpdate, HustleInputRequest
from app.schemas.pagination import PaginatedResponse
from app.services.finance_service import finance_service

router = APIRouter()


@router.get("/expenses", response_model=PaginatedResponse[ExpenseResponse])
async def read_expenses(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    return await finance_service.list(db, current_user.id, page, limit)


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    expense_id: int,
    expense_in: ExpenseUpdate,
) -> Any:
    return await finance_service.update(db, current_user.id, expense_id, expense_in)


@router.delete("/expenses/{expense_id}", response_model=ExpenseResponse)
async def delete_expense(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    expense_id: int,
) -> Any:
    return await finance_service.delete(db, current_user.id, expense_id)


@router.post("/hustle-input", response_model=ExpenseResponse)
@limiter.limit("10/minute")
async def create_hustle_expense(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    hustle_in: HustleInputRequest = ...,
) -> Any:
    return await finance_service.create_from_text(db, current_user.id, hustle_in)

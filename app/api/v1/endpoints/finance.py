from math import ceil
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.core.limiter import limiter
from app.schemas.pagination import PaginatedResponse
from app.models.user import User
from app.models.finance import Expense
from app.schemas.finance import (
    ExpenseResponse, HustleInputRequest
)
from app.services.ai_service import ai_service

router = APIRouter()

@router.get("/expenses", response_model=PaginatedResponse[ExpenseResponse])
async def read_expenses(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    """
    Retrieve expenses for current user (paginated).
    """
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count(Expense.id)).where(Expense.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Expense)
        .where(Expense.user_id == current_user.id)
        .order_by(Expense.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )

    return {
        "items": result.scalars().all(),
        "total": total,
        "page": page,
        "pages": ceil(total / limit) if total > 0 else 1,
    }

@router.delete("/expenses/{expense_id}", response_model=ExpenseResponse)
async def delete_expense(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    expense_id: int
) -> Any:
    """
    Delete an expense.
    """
    result = await db.execute(
        select(Expense)
        .where(Expense.id == expense_id, Expense.user_id == current_user.id)
    )
    expense = result.scalars().first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    await db.delete(expense)
    await db.commit()
    return expense

@router.post("/hustle-input", response_model=ExpenseResponse)
@limiter.limit("10/minute")
async def create_hustle_expense(
    request: Request,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    hustle_in: HustleInputRequest = ...,
) -> Any:
    """
    AI-powered hustle input for quick expense tracking.
    """
    # Use AI to parse the input
    parsed_data = await ai_service.parse_hustle_input(hustle_in.text)
    
    if "error" in parsed_data:
        raise HTTPException(status_code=400, detail=f"Failed to parse input: {parsed_data['error']}")
    
    # Validate parsed data
    amount = parsed_data.get("amount")
    category = hustle_in.forced_category or parsed_data.get("category")
    description = parsed_data.get("description")
    
    # Handle missing amount specifically
    if amount is None:
        raise HTTPException(status_code=400, detail="Couldn't find the amount in your text. Example: '50 PLN for pizza'")

    if category is None or description is None:
        raise HTTPException(status_code=400, detail="AI couldn't categorize the expense reliably.")
    
    # Save to database
    db_obj = Expense(
        amount=float(amount),
        category=category.upper(), # Ensure uppercase to match enum
        description=description,
        user_id=current_user.id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

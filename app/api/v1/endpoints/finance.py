from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.finance import Asset, Transaction, Expense
from app.schemas.finance import (
    AssetCreate, AssetResponse,
    TransactionCreate, TransactionResponse,
    AssetPortfolioResponse,
    ExpenseResponse, HustleInputRequest
)
from app.services.ai_service import ai_service

router = APIRouter()

@router.get("/expenses", response_model=List[ExpenseResponse])
async def read_expenses(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve expenses for current user.
    """
    result = await db.execute(
        select(Expense)
        .where(Expense.user_id == current_user.id)
        .order_by(Expense.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

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
async def create_hustle_expense(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    hustle_in: HustleInputRequest
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
        raise HTTPException(status_code=400, detail="Nie udało się znaleźć kwoty w tekście. Podaj np. '50 zł na pizzę'")

    if category is None or description is None:
        raise HTTPException(status_code=400, detail="AI nie było w stanie poprawnie skategoryzować wydatku.")
    
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

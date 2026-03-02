from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.finance import Asset, Transaction
from app.schemas.finance import (
    AssetCreate, AssetResponse,
    TransactionCreate, TransactionResponse,
    AssetPortfolioResponse
)

router = APIRouter()

@router.post("/assets", response_model=AssetResponse)
async def create_asset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    asset_in: AssetCreate
) -> Any:
    db_obj = Asset(**asset_in.model_dump(), user_id=current_user.id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    tx_in: TransactionCreate
) -> Any:
    # Check asset ownership
    result = await db.execute(
        select(Asset).where(
            Asset.id == tx_in.asset_id,
            Asset.user_id == current_user.id
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Asset not found")
        
    tx_data = tx_in.model_dump()
    if tx_data.get("timestamp") and hasattr(tx_data["timestamp"], "tzinfo") and tx_data["timestamp"].tzinfo is not None:
        tx_data["timestamp"] = tx_data["timestamp"].replace(tzinfo=None)
        
    db_obj = Transaction(**tx_data)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


@router.delete("/assets/{asset_id}", response_model=AssetResponse)
async def delete_asset(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    asset_id: int
) -> Any:
    result = await db.execute(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.user_id == current_user.id
        )
    )
    asset = result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await db.delete(asset)
    await db.commit()
    return asset


@router.delete("/transactions/{transaction_id}", response_model=TransactionResponse)
async def delete_transaction(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    transaction_id: int
) -> Any:
    result = await db.execute(
        select(Transaction)
        .join(Asset)
        .where(
            Transaction.id == transaction_id,
            Asset.user_id == current_user.id
        )
    )
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await db.delete(transaction)
    await db.commit()
    return transaction

@router.get("/portfolio", response_model=List[AssetPortfolioResponse])
async def get_portfolio(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Fetch all user assets with calculated quantity and average buy price.
    """
    result = await db.execute(
        select(Asset)
        .where(Asset.user_id == current_user.id)
        .options(selectinload(Asset.transactions))
    )
    return result.scalars().all()

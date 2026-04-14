from math import ceil
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.job_offer import JobOffer
from app.schemas.offers import JobOfferCreate, JobOfferResponse, JobOfferUpdate
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post("/offers", response_model=JobOfferResponse)
async def create_offer(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    offer_in: JobOfferCreate,
) -> Any:
    db_obj = JobOffer(**offer_in.model_dump(mode="json"), user_id=current_user.id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


@router.get("/offers", response_model=PaginatedResponse[JobOfferResponse])
async def read_offers(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    offset = (page - 1) * limit

    count_result = await db.execute(
        select(func.count(JobOffer.id)).where(JobOffer.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(JobOffer)
        .where(JobOffer.user_id == current_user.id)
        .order_by(JobOffer.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return {
        "items": result.scalars().all(),
        "total": total,
        "page": page,
        "pages": ceil(total / limit) if total > 0 else 1,
    }


@router.delete("/offers/{offer_id}", response_model=JobOfferResponse)
async def delete_offer(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    offer_id: int,
) -> Any:
    result = await db.execute(
        select(JobOffer).where(JobOffer.id == offer_id, JobOffer.user_id == current_user.id)
    )
    offer = result.scalars().first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    await db.delete(offer)
    await db.commit()
    return offer


@router.patch("/offers/{offer_id}", response_model=JobOfferResponse)
async def update_offer(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    offer_id: int,
    offer_in: JobOfferUpdate,
) -> Any:
    result = await db.execute(
        select(JobOffer).where(JobOffer.id == offer_id, JobOffer.user_id == current_user.id)
    )
    offer = result.scalars().first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    update_data = offer_in.model_dump(exclude_unset=True, mode="json")
    for field, value in update_data.items():
        setattr(offer, field, value)

    await db.commit()
    await db.refresh(offer)
    return offer

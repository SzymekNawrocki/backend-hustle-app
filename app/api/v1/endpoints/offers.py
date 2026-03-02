from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.job_offer import JobOffer
from app.schemas.offers import JobOfferCreate, JobOfferResponse, JobOfferUpdate

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


@router.get("/offers", response_model=List[JobOfferResponse])
async def read_offers(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    result = await db.execute(
        select(JobOffer)
        .where(JobOffer.user_id == current_user.id)
        .order_by(JobOffer.id.desc())
    )
    return result.scalars().all()


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

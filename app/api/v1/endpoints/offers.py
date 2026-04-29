from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.cache import invalidate_dashboard
from app.db.pagination import paginate
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
    await invalidate_dashboard(current_user.id)
    return db_obj


@router.get("/offers", response_model=PaginatedResponse[JobOfferResponse])
async def read_offers(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    base_filter = (JobOffer.user_id == current_user.id, JobOffer.deleted_at.is_(None))
    return await paginate(
        db,
        query=select(JobOffer).where(*base_filter).order_by(JobOffer.id.desc()),
        count_query=select(func.count(JobOffer.id)).where(*base_filter),
        page=page,
        limit=limit,
    )


@router.delete("/offers/{offer_id}", response_model=JobOfferResponse)
async def delete_offer(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    offer_id: int,
) -> Any:
    result = await db.execute(
        select(JobOffer).where(
            JobOffer.id == offer_id,
            JobOffer.user_id == current_user.id,
            JobOffer.deleted_at.is_(None),
        )
    )
    offer = result.scalars().first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    offer.soft_delete()
    await db.commit()
    await invalidate_dashboard(current_user.id)
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
        select(JobOffer).where(
            JobOffer.id == offer_id,
            JobOffer.user_id == current_user.id,
            JobOffer.deleted_at.is_(None),
        )
    )
    offer = result.scalars().first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    update_data = offer_in.model_dump(exclude_unset=True, mode="json")
    for field, value in update_data.items():
        setattr(offer, field, value)

    await db.commit()
    await db.refresh(offer)
    await invalidate_dashboard(current_user.id)
    return offer

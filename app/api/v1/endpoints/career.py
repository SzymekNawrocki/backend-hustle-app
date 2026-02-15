from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api import deps
from app.models.user import User
from app.models.career import JobApplication, Interview
from app.models.profile import UserProfile
from app.schemas.career import (
    JobApplicationCreate, JobApplicationResponse,
    InterviewCreate, InterviewResponse,
    JobDescriptionRequest, CareerAnalysisResponse,
    UserProfileResponse, UserProfileUpdate
)
from app.schemas.ai import JobAnalysisAIResponse
from app.services.ai_service import ai_service

router = APIRouter()

@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Get current user's career profile.
    """
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    
    if not profile:
        return UserProfile(user_id=current_user.id)
    return profile


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    profile_in: UserProfileUpdate
) -> Any:
    """
    Update or create career profile/CV.
    """
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    db_obj = result.scalars().first()

    if db_obj:
        update_data = profile_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
    else:
        db_obj = UserProfile(**profile_in.model_dump(), user_id=current_user.id)
        db.add(db_obj)
    
    await db.commit()
    await db.refresh(db_obj)
    return db_obj



@router.post("/applications", response_model=JobApplicationResponse)
async def create_application(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    app_in: JobApplicationCreate
) -> Any:
    db_obj = JobApplication(**app_in.model_dump(), user_id=current_user.id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.get("/applications", response_model=List[JobApplicationResponse])
async def read_applications(
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    result = await db.execute(
        select(JobApplication)
        .where(JobApplication.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .options(selectinload(JobApplication.interviews))
    )
    return result.scalars().all()

@router.post("/analyze", response_model=CareerAnalysisResponse)
async def analyze_job(
    *,
    db: AsyncSession = Depends(deps.get_db),
    input_data: JobDescriptionRequest,
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    """
    Perform deep AI analysis of a job description against the user's CV.
    """
    # Fetch profile if not already loaded
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    
    cv_text = profile.cv_text if profile else ""

    if not cv_text:
        raise HTTPException(
            status_code=400, 
            detail="User career profile (CV) is empty. Please update your profile first."
        )

    ai_data = await ai_service.analyze_job_fit(input_data.description, cv_text)
    
    if "error" in ai_data:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=ai_data.get("details", "AI Error"))
    
    # Validate and structure
    try:
        analysis = JobAnalysisAIResponse(**ai_data)
        return {
            "match_score": analysis.match_score,
            "pros": analysis.matching_keywords,
            "cons": [],
            "missing_skills": analysis.missing_skills,
            "summary": f"Based on your CV, you have a {analysis.match_score}% match for this position."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI output validation failed: {e}")

@router.post("/interviews", response_model=InterviewResponse)
async def create_interview(
    *,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    interview_in: InterviewCreate
) -> Any:
    # Check ownership
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == interview_in.application_id,
            JobApplication.user_id == current_user.id
        )
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Job Application not found")
        
    db_obj = Interview(**interview_in.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

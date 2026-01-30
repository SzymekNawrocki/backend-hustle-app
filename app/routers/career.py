from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.career import JobApplication
from app.models.user import UserProfile
from app.schemas.career import JobApplicationCreate, JobApplicationResponse
from app.services.ai_engine import AIEngine

ai_engine = AIEngine()

router = APIRouter(prefix="/career", tags=["Career"])

@router.post("/analyze")
async def analyze_listing(description: str, db: Session = Depends(get_db)):
    """
    Analyzes a job description text using Groq AI and real UserProfile data.
    """
    profile = db.query(UserProfile).first()
    if profile:
        user_profile = {
            "full_name": profile.full_name,
            "job_title": profile.job_title,
            "skills": profile.skills,
            "experience_years": profile.experience_years,
            "bio": profile.bio
        }
    else:
        user_profile = {
            "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
            "experience_years": 5
        }
    
    analysis = await ai_engine.analyze_job(description, user_profile)
    
    if not analysis:
        return {"status": "pending", "message": "AI analysis is currently unavailable. Please try again later."}
        
    return analysis

@router.post("/apply", response_model=JobApplicationResponse)
async def create_application(application: JobApplicationCreate, db: Session = Depends(get_db)):
    """
    Creates a new job application. If description_raw is provided, it automatically
    runs AI analysis using Groq and saves the results.
    """
    db_application = JobApplication(**application.model_dump())
    
    if db_application.description_raw:
        profile = db.query(UserProfile).first()
        if profile:
            user_profile = {
                "full_name": profile.full_name,
                "job_title": profile.job_title,
                "skills": profile.skills,
                "experience_years": profile.experience_years,
                "bio": profile.bio
            }
        else:
            user_profile = {
                "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
                "experience_years": 5
            }
        
        analysis = await ai_engine.analyze_job(db_application.description_raw, user_profile)
        
        if analysis:
            db_application.match_score = analysis.get("match_score")
            db_application.ai_analysis = analysis
            # Backward compatibility for existing fields if needed
            db_application.ai_keywords = analysis.get("missing_skills", [])
        
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    return db_application

@router.get("/applications", response_model=List[JobApplicationResponse])
def list_applications(db: Session = Depends(get_db)):
    """
    Returns a list of all job applications.
    """
    return db.query(JobApplication).all()

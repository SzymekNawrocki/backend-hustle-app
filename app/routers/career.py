from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.career import JobApplication
from app.schemas.career import JobApplicationCreate, JobApplicationResponse
from app.services.ai_career import analyze_job_description

router = APIRouter(prefix="/career", tags=["Career"])

@router.post("/analyze")
async def analyze_listing(description: str):
    """
    Analyzes a job description text without saving it to the database.
    """
    analysis = analyze_job_description(description)
    return analysis

@router.post("/apply", response_model=JobApplicationResponse)
def create_application(application: JobApplicationCreate, db: Session = Depends(get_db)):
    """
    Creates a new job application. If description_raw is provided, it automatically
    runs AI analysis and saves the results.
    """
    db_application = JobApplication(**application.model_dump())
    
    if db_application.description_raw:
        analysis = analyze_job_description(db_application.description_raw)
        db_application.match_score = analysis["match_score"]
        db_application.ai_keywords = analysis["ai_keywords"]
        
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

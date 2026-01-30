from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import UserProfile
from app.schemas.user import UserProfileUpdate, UserProfileResponse
from app.services.ai_engine import AIEngine

router = APIRouter(prefix="/user", tags=["User"])
ai_engine = AIEngine()

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    """
    Returns the user profile. Creates a default one if it doesn't exist.
    """
    profile = db.query(UserProfile).first()
    if not profile:
        # Create a default profile for demo purposes
        profile = UserProfile(
            full_name="Jan Nowak",
            job_title="Python Developer",
            bio="Passionate about AI and Backend development.",
            skills=[{"name": "Python", "level": 8}]
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile

@router.put("/profile", response_model=UserProfileResponse)
def update_profile(profile_data: UserProfileUpdate, db: Session = Depends(get_db)):
    """
    Updates the user profile.
    """
    db_profile = db.query(UserProfile).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_dict = profile_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(db_profile, key, value)
        
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.post("/profile/sync-ai")
async def sync_profile_with_ai(cv_text: str, db: Session = Depends(get_db)):
    """
    Analyzes raw CV text and updates the user's skills using Groq AI.
    """
    db_profile = db.query(UserProfile).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    extracted_skills = await ai_engine.sync_profile_skills(cv_text)
    
    if extracted_skills:
        db_profile.skills = extracted_skills
        db.commit()
        db.refresh(db_profile)
        return {"status": "success", "skills": extracted_skills}
    else:
        raise HTTPException(status_code=500, detail="Failed to extract skills via AI")

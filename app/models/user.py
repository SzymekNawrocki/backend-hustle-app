from sqlalchemy import Column, Integer, String, Text, JSON
from app.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    job_title = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    experience_years = Column(Integer, default=0)
    skills = Column(JSON, nullable=True)  # List of objects: [{"name": "Python", "level": 8}]

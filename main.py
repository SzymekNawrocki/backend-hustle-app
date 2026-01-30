import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class HustleItem(Base):
    __tablename__ = "hustle_items"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String)
    title = Column(String)
    value = Column(Float)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/status")
def get_status():
    return {"status": "Hustle API Online", "message": "Działa kurwa!"}

@app.post("/items")
def create_item(title: str, category: str, value: float, db: Session = Depends(get_db)):
    new_item = HustleItem(title=title, category=category, value=value)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"status": "Zapisano w bazie!", "data": new_item}

@app.get("/items")
def get_items(db: Session = Depends(get_db)):
    items = db.query(models.HustleItem).all()
    return items
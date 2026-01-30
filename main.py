from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, crud, database
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Hustle API Pro")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/items", response_model=schemas.HustleItemResponse)
def create_item(item: schemas.HustleItemCreate, db: Session = Depends(database.get_db)):
    return crud.create_item(db=db, item=item)

@app.get("/items", response_model=List[schemas.HustleItemResponse])
def read_items(db: Session = Depends(database.get_db)):
    return crud.get_items(db=db)

@app.get("/")
def root():
    return {"message": "API po refaktoryzacji działa!"}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app import models
from app.routers import career, finance, user

# Create database tables (usually handled by Alembic, but good for dev)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hustle App API",
    description="Backend for the Hustle App - Career & AI Support module included.",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(career.router)
app.include_router(finance.router)
app.include_router(user.router)

@app.get("/")
def read_root():
    return {"status": "success", "message": "Hustle App API is running!"}

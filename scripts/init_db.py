import asyncio
import sys
import os

# Add parrent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base
from app.db.session import engine

async def init_db():
    print("Connecting to database...")
    try:
        async with engine.begin() as conn:
            # This will create all tables defined in app/db/base.py
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())

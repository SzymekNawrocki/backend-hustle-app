import asyncio
from app.db.session import engine
from app.core import security
from app.core.config import settings
from app.db.base_class import Base
from sqlalchemy import text

async def check_db_connection():
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"SUCCESS: Database connection successful: {result.fetchone()}")
    except Exception as e:
        print(f"FAILED: Database connection failed: {e}")

def check_security():
    try:
        password = "secret_password"
        hashed = security.get_password_hash(password)
        print(f"SUCCESS: Password hashing: {hashed[:20]}...")
        
        verified = security.verify_password(password, hashed)
        print(f"SUCCESS: Password verification: {verified}")
        
        token = security.create_access_token(subject=1)
        print(f"SUCCESS: JWT Token generation: {token[:20]}...")
    except Exception as e:
        import traceback
        print(f"FAILED: Security check failed: {e}")
        traceback.print_exc()

def check_config():
    print(f"SUCCESS: Project Name: {settings.PROJECT_NAME}")
    print(f"SUCCESS: Async DB URL: {settings.ASYNC_DATABASE_URL[:30]}...")

async def main():
    print("--- HustleOS Verification ---")
    check_config()
    check_security()
    await check_db_connection()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

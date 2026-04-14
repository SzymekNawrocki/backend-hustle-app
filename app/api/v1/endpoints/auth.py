from fastapi import APIRouter, Depends, HTTPException, Request, status, Response, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.demo_service import reset_demo_data


router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserCreate
) -> Any:
    # Sprawdzenie czy użytkownik istnieje
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Użytkownik z tym mailem już istnieje.",
        )
    
    # Tworzenie nowego użytkownika
    db_obj = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.post("/login", response_model=Token)
@limiter.limit("5/minute", key_func=get_remote_address)
async def login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    # Szukanie użytkownika po emailu (form_data.username)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    # Weryfikacja hasła
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Niepoprawny email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Użytkownik nieaktywny")
    
    # Generowanie tokena
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(deps.get_current_user)
) -> Any:
    return current_user

@router.post("/demo-login", response_model=Token)
async def demo_login(
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    DEMO_EMAIL = "guest@demo.com"
    
    # 1. Sprawdź czy użytkownik demo istnieje, jeśli nie - stwórz
    result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
    user = result.scalars().first()
    
    if not user:
        user = User(
            email=DEMO_EMAIL,
            hashed_password=security.get_password_hash("demo-guest-password-not-needed"),
            full_name="Demo Guest",
            is_demo=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # 2. Resetuj dane demo w tle, aby logowanie było natychmiastowe
    # background_tasks.add_task(reset_demo_data, db, user.id) 
    # Uwaga: Musimy upewnić się, że db session jest żywa. Lepiej zrobić to tutaj przed returnem ale zoptymalizowane.
    # Na razie zostawimy resetowanie synchronicznie ale zoptymalizujemy zapytania jeśli trzeba.
    await reset_demo_data(db, user.id)
    
    # 3. Generowanie tokena
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(response: Response) -> Any:
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    return {"status": "ok"}

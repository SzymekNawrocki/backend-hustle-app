# HustleOS — Backend

Backend aplikacji HustleOS: platforma do śledzenia celów, finansów osobistych i zdrowia z integracją AI.

## Stack

- **FastAPI** — framework REST API (async)
- **SQLAlchemy 2.0 + asyncpg** — ORM z pełną obsługą async
- **PostgreSQL** — baza danych (Supabase / Neon)
- **Alembic** — migracje schematu
- **Groq API** (Llama 3.3-70b) — parsowanie AI
- **slowapi** — rate limiting per-user
- **Docker** — konteneryzacja (multi-stage build)
- **Render.com** — deployment

## Funkcjonalności

### Autentykacja
- Rejestracja i logowanie z JWT w httpOnly cookie
- Demo login — konto gościa z resetem danych przy każdym logowaniu

### Cele (OKR)
- Tworzenie celów z milestones i zadaniami
- Smart-create — generowanie celu z krótkim opisem przez AI
- Śledzenie nawyków (daily / weekly) ze streaks
- Dashboard z podsumowaniem dnia i 7-dniową historią aktywności

### Finanse
- Dodawanie wydatków przez AI (`/hustle-input`) — wystarczy napisać "wydałem 50 zł na Żappkę"
- Kategorie: OPLATY, HUSTLE, LIFESTYLE, INCOME
- Historia z paginacją

### Zdrowie
- Logowanie posiłków przez AI — opis w naturalnym języku → makra (kalorie, białko, węglowodany, tłuszcze)
- Historia z paginacją

### Oferty pracy
- Pipeline ofert z etapami: Wysłano → 1 etap → 2 etap → 3 etap → Umowa

## Uruchomienie lokalnie

```bash
# 1. Sklonuj repozytorium
git clone <repo-url>
cd backend

# 2. Utwórz środowisko wirtualne
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Zainstaluj zależności
pip install -r requirements.txt

# 4. Skonfiguruj zmienne środowiskowe
cp .env.example .env
# Uzupełnij DATABASE_URL, SECRET_KEY, GROQ_API_KEY

# 5. Uruchom migracje
alembic upgrade head

# 6. Uruchom serwer
uvicorn app.main:app --reload
```

API dostępne pod `http://localhost:8000`. Dokumentacja Swagger: `http://localhost:8000/docs`.

## Docker

```bash
docker build -t hustle-backend .
docker run -p 8000:8000 --env-file .env hustle-backend
```

## Zmienne środowiskowe

| Zmienna | Opis | Wymagana |
|---|---|---|
| `DATABASE_URL` | Connection string PostgreSQL | tak |
| `SECRET_KEY` | Klucz JWT (min. 32 znaki) | tak |
| `GROQ_API_KEY` | Klucz API Groq | tak |
| `DB_SSL` | SSL dla bazy (true w produkcji) | nie |
| `BACKEND_CORS_ORIGINS` | Dozwolone originy CORS | nie |

Szablon: `.env.example`

## Testy

```bash
pytest
```

## Migracje

```bash
# Nowa migracja
alembic revision --autogenerate -m "opis zmian"

# Zastosuj migracje
alembic upgrade head

# Rollback
alembic downgrade -1
```

Nie modyfikuj plików migracji ręcznie.

## Struktura projektu

```
app/
├── api/v1/endpoints/   # Endpointy (auth, goals, finance, health, offers)
├── core/               # Konfiguracja, JWT, rate limiting
├── db/                 # Sesja, typy, base class
├── models/             # Modele SQLAlchemy
├── schemas/            # Schematy Pydantic
└── services/           # Logika biznesowa, integracja AI
```

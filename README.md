# HustleOS — Backend

Backend for HustleOS: a personal productivity and finance tracking platform with AI integration.

## Stack

- **FastAPI** — async REST API framework
- **SQLAlchemy 2.0 + asyncpg** — async ORM
- **PostgreSQL** — database (Supabase / Neon)
- **Alembic** — schema migrations
- **Groq API** (Llama 3.3-70b) — AI parsing
- **slowapi** — per-user rate limiting
- **Docker** — multi-stage containerization
- **Render.com** — deployment

## Features

### Authentication
- Registration and login with JWT stored in an httpOnly cookie
- Demo login — guest account with data reset on every login

### Goals (OKR)
- Create goals with milestones and tasks
- Smart-create — generate a full goal from a short description using AI
- Habit tracking (daily / weekly) with streaks
- Dashboard with a daily summary and 7-day activity history

### Finance
- Add expenses via AI (`/hustle-input`) — just describe what you spent in plain text
- Categories: OPLATY, HUSTLE, LIFESTYLE, INCOME
- Paginated expense history

### Health
- Log meals via AI — natural language description → macros (calories, protein, carbs, fat)
- Paginated meal history

### Job offers
- Job offer pipeline with stages: Wysłano → 1 etap → 2 etap → 3 etap → Umowa

## Running locally

```bash
# 1. Clone the repository
git clone <repo-url>
cd backend

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Fill in DATABASE_URL, SECRET_KEY, GROQ_API_KEY

# 5. Run migrations
alembic upgrade head

# 6. Start the server
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Swagger docs: `http://localhost:8000/docs`.

## Docker

```bash
docker build -t hustle-backend .
docker run -p 8000:8000 --env-file .env hustle-backend
```

## Environment variables

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | yes |
| `SECRET_KEY` | JWT secret key (min. 32 chars) | yes |
| `GROQ_API_KEY` | Groq API key | yes |
| `DB_SSL` | SSL for database (true in production) | no |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins | no |

Template: `.env.example`

## Tests

```bash
pytest
```

## Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Do not modify migration files manually.

## Project structure

```
app/
├── api/v1/endpoints/   # Routers (auth, goals, finance, health, offers)
├── core/               # Config, JWT, rate limiting
├── db/                 # Session, types, base class
├── models/             # SQLAlchemy models
├── schemas/            # Pydantic schemas
└── services/           # Business logic, AI integration
```

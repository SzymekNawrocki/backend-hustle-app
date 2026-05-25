# Hustle App — Backend

Personal productivity and finance tracking platform with AI-powered parsing, JWT authentication, and async PostgreSQL.

## Table of Contents

- [Stack](#stack)
- [Architecture](#architecture)
- [Running Locally](#running-locally)
- [Environment Variables](#environment-variables)
- [Docker](#docker)
- [API Reference](#api-reference)
- [Authentication Flow](#authentication-flow)
- [AI Integration](#ai-integration)
- [Data Models](#data-models)
- [Rate Limiting](#rate-limiting)
- [Caching](#caching)
- [Soft Deletes & Pagination](#soft-deletes--pagination)
- [Migrations](#migrations)
- [Tests & CI](#tests--ci)
- [Project Structure](#project-structure)

---

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 + asyncpg |
| Database | PostgreSQL (Neon) |
| Migrations | Alembic |
| AI | Groq API — `llama-3.3-70b-versatile` |
| Auth | JWT (HS256) + httpOnly cookies + refresh tokens |
| Rate Limiting | slowapi (per-user) |
| Error Tracking | Sentry |
| Deployment | Render.com (Docker) |

---

## Architecture

```
backend/app/
├── main.py                     # App factory, middleware, exception handlers, structured logging
├── api/
│   ├── deps.py                 # Dependency injection: DB session, current-user guard
│   └── v1/
│       ├── api.py              # Router aggregation
│       └── endpoints/
│           ├── auth.py         # Register, login, refresh, logout, demo-login
│           ├── goals.py        # Goals, milestones, tasks, habits, dashboard, smart-create
│           ├── finance.py      # Expenses, AI hustle-input
│           ├── health.py       # Meals, AI meal logging
│           ├── offers.py       # Job offer pipeline
│           └── export.py       # CSV export for expenses and meals
├── core/
│   ├── config.py               # pydantic-settings: env vars, DB URL normalisation
│   ├── security.py             # JWT creation/decode, password hashing (PBKDF2 + bcrypt fallback)
│   ├── limiter.py              # Per-user rate limiter (JWT → user_id, fallback to IP)
│   └── cache.py                # In-memory TTL cache (dashboard 30 s, activity 60 s)
├── db/
│   ├── session.py              # AsyncSessionLocal, engine, connection pool
│   ├── base.py                 # Declarative base with auto table-name mixin
│   └── types.py                # Custom column types (NaiveDateTime)
├── models/                     # SQLAlchemy ORM models
│   ├── user.py
│   ├── goal.py                 # Goal, Milestone, Task, Habit
│   ├── finance.py              # Expense
│   ├── health.py               # MealLog
│   └── job_offer.py            # JobOffer
├── schemas/                    # Pydantic request/response models
│   ├── user.py
│   ├── goal.py
│   ├── finance.py
│   ├── health.py
│   ├── offers.py
│   ├── ai.py                   # Groq response shapes
│   └── pagination.py           # Generic PaginatedResponse[T]
└── services/
    ├── auth_service.py         # Register, login, refresh, logout, demo account
    ├── goal_service.py         # Goals, milestones, tasks, habits, dashboard, activity
    ├── finance_service.py      # Expenses CRUD, AI hustle-input parsing
    ├── health_service.py       # Meal log CRUD, AI meal parsing
    ├── ai_service.py           # Groq integration (meals, expenses, goals)
    └── demo_service.py         # Demo account data seeding/reset
```

**Design principles:**
- Routers are thin — they validate input, call a service or query, and return a response.
- All business logic and AI calls live in `services/`.
- SQL aggregations happen in the DB (`func.sum`, `GROUP BY`) — never in Python loops.
- Dashboard fetches 8 queries concurrently with `asyncio.gather()`.
- All FK columns and hot `WHERE` columns carry `index=True`.

---

## Running Locally

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY (≥32 chars), GROQ_API_KEY

# 4. Apply migrations
alembic upgrade head

# 5. Start the dev server
uvicorn app.main:app --reload
```

API root: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL connection string. `postgresql://` is auto-converted to `postgresql+asyncpg://`. |
| `SECRET_KEY` | yes | JWT signing secret. Minimum 32 characters (enforced by validator). |
| `GROQ_API_KEY` | yes | Groq API key for AI features. |
| `DB_SSL` | no | Enable SSL for the DB connection (default: `true`). |
| `SENTRY_DSN` | no | Sentry DSN for error tracking. |
| `BACKEND_CORS_ORIGINS` | no | Comma-separated allowed CORS origins. Defaults to the Vercel deployment and `localhost:3000`. |

Template: `.env.example`

> **Never commit secrets.** Update `.env.example` whenever you add a required variable.

---

## Docker

```bash
docker build -t hustle-backend .
docker run -p 8000:8000 --env-file .env hustle-backend
```

The image uses a multi-stage build. Render.com pulls and runs it on every deploy.

---

## API Reference

All routes are prefixed with `/api/v1`.

### Authentication — `/auth`

| Method | Path | Auth | Limit | Description |
|---|---|---|---|---|
| POST | `/auth/register` | — | — | Create a new account |
| POST | `/auth/login` | — | 5/min | Log in; sets `token` + `refresh_token` cookies |
| POST | `/auth/refresh` | cookie | 20/min | Exchange refresh token for a new access token |
| GET | `/auth/me` | JWT | — | Return the current user's profile |
| POST | `/auth/demo-login` | — | 3/min | Log in as the demo guest; resets demo data in the background |
| POST | `/auth/logout` | JWT | — | Invalidate the refresh token |

### Goals — `/goals`

| Method | Path | Auth | Limit | Description |
|---|---|---|---|---|
| POST | `/goals/` | JWT | — | Create a goal with optional milestones and tasks |
| GET | `/goals/` | JWT | — | List goals (paginated, 20/page) |
| GET | `/goals/{id}` | JWT | — | Get a single goal |
| PATCH | `/goals/{id}` | JWT | — | Update goal fields |
| DELETE | `/goals/{id}` | JWT | — | Soft-delete a goal |
| GET | `/goals/dashboard/today` | JWT | — | Daily dashboard: tasks, macros, balance, goals (cached 30 s) |
| GET | `/goals/activity/history` | JWT | — | 7-day activity history (cached 60 s) |
| POST | `/goals/smart-create` | JWT | 10/min | Generate a full OKR from a plain-text idea via AI |
| POST | `/goals/tasks/{id}/toggle` | JWT | — | Toggle a task's completion state |
| POST | `/goals/milestones/{id}/toggle` | JWT | — | Toggle a milestone's completion state |

Goals expose a computed `progress_percentage` field (% of milestones completed).

### Finance — `/finance`

| Method | Path | Auth | Limit | Description |
|---|---|---|---|---|
| GET | `/finance/expenses` | JWT | — | List expenses (paginated, newest first) |
| PATCH | `/finance/expenses/{id}` | JWT | — | Update an expense |
| DELETE | `/finance/expenses/{id}` | JWT | — | Soft-delete an expense |
| POST | `/finance/hustle-input` | JWT | 10/min | Parse a natural-language expense description via AI |

**Hustle-input example:**
```json
// Request
{ "text": "50 PLN for a Python course" }

// Response
{ "amount": 50.0, "category": "HUSTLE", "description": "Python course" }
```

Categories: `OPLATY` (bills/food) · `HUSTLE` (courses/gear) · `LIFESTYLE` · `INCOME`

### Health — `/health`

| Method | Path | Auth | Limit | Description |
|---|---|---|---|---|
| GET | `/health/meals` | JWT | — | List meals (paginated, newest first) |
| POST | `/health/log-meal-ai` | JWT | 10/min | Parse a meal description → macros via AI |
| DELETE | `/health/meals/{id}` | JWT | — | Soft-delete a meal |

**Meal-log example:**
```json
// Request
{ "description": "oatmeal with banana and peanut butter" }

// Response
{ "description": "...", "calories": 420, "protein": 14.0, "carbs": 58.0, "fat": 12.0 }
```

### Job Offers — `/offers`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/offers` | JWT | Create a job offer |
| GET | `/offers` | JWT | List offers (paginated) |
| PATCH | `/offers/{id}` | JWT | Update offer (status, notes, company, URL) |
| DELETE | `/offers/{id}` | JWT | Soft-delete an offer |

**Status pipeline:** `wysłano` → `1 etap` → `2 etap` → `3 etap` → `umowa`

### Export — `/export`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/export/expenses.csv` | JWT | Download all expenses as CSV |
| GET | `/export/meals.csv` | JWT | Download all meals as CSV |

---

## Authentication Flow

**Token storage:** httpOnly, Secure, SameSite=none cookies (cross-origin: Vercel → Render).

**Access token:** 60-minute lifetime, HS256.

**Refresh token:**
- 64-char hex string generated with `secrets.token_hex(32)`.
- SHA-256 hashed before being stored in the DB.
- Cookie path restricted to `/api/v1/auth/refresh` to prevent leakage to other endpoints.
- 30-day lifetime.

**Password hashing:** PBKDF2-SHA256 primary; bcrypt fallback for legacy hashes.

**Guard:** `Depends(deps.get_current_user)` is required on every endpoint that reads or writes user data. Auth errors always return a generic `"Could not validate credentials"` message — the specific failure reason is never exposed.

---

## AI Integration

Provider: **Groq** (`AsyncGroq`)  
Model: **`llama-3.3-70b-versatile`**  
Response format: `json_object` for deterministic parsing.

| Feature | Endpoint | Temp | Output |
|---|---|---|---|
| Parse meal → macros | `POST /health/log-meal-ai` | 0.7 | `{calories, protein, carbs, fat}` |
| Parse expense | `POST /finance/hustle-input` | 0.0 | `{amount, category, description}` |
| Generate OKR | `POST /goals/smart-create` | 0.7 | `{title, description, milestones[], tasks[]}` |

**Input constraints (enforced by Pydantic):**
- General text fields sent to AI: `max_length=1000`
- Idea / goal inputs: `max_length=500`

**Error handling:** `RateLimitError` and `APIConnectionError` return HTTP 502 with `{"error": "AI service temporarily unavailable"}`. JSON decode failures also return 502.

---

## Data Models

### User
```
id, email (unique), hashed_password, full_name, is_active, is_demo
refresh_token_hash, refresh_token_expires_at
```

### Goal / Milestone / Task / Habit
```
Goal:      id, title, description, category (CAREER|FINANCE|HEALTH|PERSONAL),
           target_date, status (IN_PROGRESS|COMPLETED|ARCHIVED), deleted_at, user_id

Milestone: id, title, is_completed, goal_id

Task:      id, title, description, is_completed, due_date, deleted_at, user_id, goal_id?

Habit:     id, title, frequency (DAILY|WEEKLY), streak, user_id
```

### Expense
```
id, amount, category (OPLATY|HUSTLE|LIFESTYLE|INCOME),
description, timestamp (indexed), deleted_at, user_id
```

### MealLog
```
id, description, calories, protein, carbs, fat,
created_at (indexed), deleted_at, user_id
```

### JobOffer
```
id, title, company, status (wysłano|1 etap|2 etap|3 etap|umowa),
url, notes, deleted_at, user_id
```

All `user_id` foreign keys and hot `WHERE`/`ORDER BY` columns carry `index=True`.

---

## Rate Limiting

Implemented with **slowapi**. Limits are per user (extracted from the JWT), with IP as fallback.

| Endpoint | Limit |
|---|---|
| `POST /auth/login` | 5 / minute |
| `POST /auth/refresh` | 20 / minute |
| `POST /auth/demo-login` | 3 / minute |
| `POST /goals/smart-create` | 10 / minute |
| `POST /finance/hustle-input` | 10 / minute |
| `POST /health/log-meal-ai` | 10 / minute |

Exceeding a limit returns HTTP 429.

---

## Caching

In-memory TTL cache (single Render instance — no Redis required on the free tier).

| Data | TTL | Invalidated on |
|---|---|---|
| Dashboard (`/goals/dashboard/today`) | 30 s | Any goal, expense, meal, or offer write |
| Activity history (`/goals/activity/history`) | 60 s | Any goal write |

The cache is ready to be swapped for Redis without changing endpoint code.

---

## Soft Deletes & Pagination

**Soft deletes:** Models have a `deleted_at: Optional[datetime]` column. Deletion sets this field; all queries filter with `.where(Model.deleted_at.is_(None))`. Nothing is physically removed.

**Pagination:** All list endpoints return:
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "pages": 3
}
```
Default: `page=1`, `limit=20`, `max_limit=100`.

---

## Migrations

```bash
# Generate a migration from model changes
alembic revision --autogenerate -m "short description"

# Apply all pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

> Never edit migration files manually. After adding `index=True` to any column, generate a new migration and run `alembic upgrade head` locally before merging.

---

## Tests & CI

### Running tests locally

```bash
cd backend
pytest -v --cov=app --cov-report=term-missing
```

Tests live in `backend/tests/` and use `pytest-asyncio` for async endpoint coverage.

### Full CI check (mirrors the pipeline)

```bash
ruff check .                          # linting + import order
mypy app --ignore-missing-imports     # type checking
bandit -r app -ll                     # static security scan (medium+ severity)
pip-audit -r requirements.txt         # known CVEs in dependencies
pytest --cov=app                      # tests with coverage
```

### CI pipeline (GitHub Actions)

**Backend** (`.github/workflows/backend-ci.yml`) runs on every push to `main` and every PR:
1. `ruff check .`
2. `mypy app --ignore-missing-imports`
3. `bandit -r app -ll`
4. `pip-audit -r requirements.txt`
5. `pytest --cov=app`

**Frontend** (`.github/workflows/frontend-ci.yml`):
1. `eslint`
2. `tsc --noEmit`
3. `next build`

Coverage must never decrease between commits.

---

## Project Structure

```
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── goals.py
│   │           ├── finance.py
│   │           ├── health.py
│   │           ├── offers.py
│   │           └── export.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── limiter.py
│   │   └── cache.py
│   ├── db/
│   │   ├── session.py
│   │   ├── base.py
│   │   └── types.py
│   ├── models/
│   │   ├── user.py
│   │   ├── goal.py
│   │   ├── finance.py
│   │   ├── health.py
│   │   └── job_offer.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── goal.py
│   │   ├── finance.py
│   │   ├── health.py
│   │   ├── offers.py
│   │   ├── ai.py
│   │   └── pagination.py
│   └── services/
│       ├── auth_service.py
│       ├── goal_service.py
│       ├── finance_service.py
│       ├── health_service.py
│       ├── ai_service.py
│       └── demo_service.py
├── alembic/                    # Migration scripts
├── tests/
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_auth.py
│   ├── test_endpoints.py
│   └── test_schemas.py
├── .env.example
├── requirements.txt
├── Dockerfile
└── alembic.ini
```

# =============================================================================
# Stage 1 — builder
# Instaluje zależności do izolowanego venv. Nie trafia do finalnego obrazu.
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Tworzymy venv w stałej ścieżce, żeby stage 2 mógł go skopiować bez zmian.
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Kopiujemy tylko requirements żeby warstwa była cache'owana niezależnie od kodu.
COPY requirements.txt .

RUN pip install --upgrade pip --quiet && \
    pip install --no-cache-dir -r requirements.txt --quiet

# =============================================================================
# Stage 2 — runtime
# Minimalny obraz: tylko venv + kod aplikacji, bez narzędzi budowania.
# =============================================================================
FROM python:3.11-slim AS runtime

# Użytkownik bez uprawnień roota — dobra praktyka bezpieczeństwa.
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid 1001 --no-create-home appuser

WORKDIR /app

# Kopiujemy zainstalowane paczki z builder stage.
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Kopiujemy kod aplikacji.
# .dockerignore wyklucza venv/, __pycache__, .env itp.
COPY . .

# Ustawiamy właściciela plików na appuser.
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Render.com wstrzykuje zmienną $PORT automatycznie.
# Lokalnie fallback na 8000.
# UWAGA: migracje uruchamia się osobno (render pre-deploy command lub ręcznie).
#   alembic upgrade head
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

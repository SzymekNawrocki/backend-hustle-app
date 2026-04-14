"""
Smoke testy aplikacji.

Nie testują logiki biznesowej ani bazy danych — sprawdzają, że:
- aplikacja importuje się bez błędów
- podstawowe endpointy odpowiadają poprawnie
- konfiguracja (Settings) jest spójna

TestClient z FastAPI działa synchronicznie i nie wymaga uruchomionej bazy danych
dla endpointów które nie wykonują zapytań (/, /health-check łapie wyjątek DB).
"""

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Import / konfiguracja
# ---------------------------------------------------------------------------

def test_app_instance_exists():
    """Aplikacja FastAPI tworzy się bez błędów."""
    assert app is not None
    assert app.title == "HustleOS"


def test_settings_loaded():
    """Settings wczytuje się i waliduje SECRET_KEY."""
    assert settings.PROJECT_NAME == "HustleOS"
    assert len(settings.SECRET_KEY) >= 32
    assert settings.API_V1_STR == "/api/v1"


# ---------------------------------------------------------------------------
# Root endpoints
# ---------------------------------------------------------------------------

def test_root_returns_200():
    """GET / zwraca 200 z polem status."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "message" in body


def test_health_check_returns_200():
    """
    GET /health-check zwraca 200.

    W CI nie ma bazy danych, więc endpoint zwróci status='error',
    ale sam HTTP response powinien być 200 (błąd DB jest obsługiwany przez try/except).
    """
    response = client.get("/health-check")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "version" in body
    # version powinno pasować do settings
    assert body["version"] == settings.VERSION


# ---------------------------------------------------------------------------
# Auth endpoints — tylko kształt odpowiedzi, bez trafień do DB
# ---------------------------------------------------------------------------

def test_login_without_credentials_returns_422():
    """
    POST /api/v1/auth/login bez body zwraca 422 Unprocessable Entity.
    Weryfikuje że endpoint istnieje i FastAPI waliduje dane wejściowe.
    """
    response = client.post(f"{settings.API_V1_STR}/auth/login")
    assert response.status_code == 422


def test_register_without_body_returns_422():
    """POST /api/v1/auth/register bez body zwraca 422."""
    response = client.post(f"{settings.API_V1_STR}/auth/register")
    assert response.status_code == 422


def test_protected_endpoint_without_token_returns_401():
    """
    GET /api/v1/goals/ bez tokena zwraca 401.
    Weryfikuje że middleware autentykacji działa.
    """
    response = client.get(f"{settings.API_V1_STR}/goals/")
    assert response.status_code == 401


def test_openapi_schema_available():
    """Schemat OpenAPI jest dostępny pod /api/v1/openapi.json."""
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "HustleOS"

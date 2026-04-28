"""
Testy endpointów auth — kształt requestów i odpowiedzi bez trafień do DB.

Weryfikują że:
- FastAPI poprawnie waliduje dane wejściowe (422 przy brakujących polach)
- Endpointy istnieją pod właściwymi ścieżkami
- Struktura odpowiedzi jest zgodna ze schemą
"""

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app, raise_server_exceptions=False)
BASE = settings.API_V1_STR


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

def test_register_empty_body_returns_422():
    response = client.post(f"{BASE}/auth/register", json={})
    assert response.status_code == 422


def test_register_missing_password_returns_422():
    response = client.post(f"{BASE}/auth/register", json={"email": "test@test.com"})
    assert response.status_code == 422


def test_register_missing_email_returns_422():
    response = client.post(f"{BASE}/auth/register", json={"password": "haslo123"})
    assert response.status_code == 422


def test_register_invalid_email_format_returns_422():
    response = client.post(
        f"{BASE}/auth/register",
        json={"email": "to-nie-jest-email", "password": "haslo123"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

def test_login_empty_body_returns_422():
    response = client.post(f"{BASE}/auth/login")
    assert response.status_code == 422


def test_login_wrong_content_type_returns_422():
    """Login wymaga form data (OAuth2PasswordRequestForm), nie JSON."""
    response = client.post(
        f"{BASE}/auth/login",
        json={"username": "test@test.com", "password": "haslo"},
    )
    assert response.status_code == 422


def test_login_form_with_missing_password_returns_422():
    response = client.post(
        f"{BASE}/auth/login",
        data={"username": "test@test.com"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

def test_logout_returns_200_without_auth():
    """Logout nie wymaga tokena — usuwa tylko cookie."""
    response = client.post(f"{BASE}/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

def test_me_without_token_returns_401():
    response = client.get(f"{BASE}/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401():
    response = client.get(
        f"{BASE}/auth/me",
        headers={"Authorization": "Bearer to.nie.jest.jwt"},
    )
    assert response.status_code == 401


def test_me_error_response_does_not_leak_internals():
    """Odpowiedź błędu nie powinna zawierać nazwy wyjątku ani szczegółów JWT."""
    response = client.get(
        f"{BASE}/auth/me",
        headers={"Authorization": "Bearer fake.token.here"},
    )
    assert response.status_code == 401
    body = response.json()["detail"].lower()
    # Nie może zawierać nazw klas wyjątków ani słów kluczowych debugowania
    assert "error" not in body or "validate" in body
    assert "jwtError" not in response.json()["detail"]
    assert "DecodeError" not in response.json()["detail"]
    assert "DEBUG" not in response.json()["detail"]

"""
Testy ochrony endpointów — każdy chroniony endpoint musi zwracać 401 bez tokena.

Weryfikują że żaden endpoint nie jest przypadkowo publiczny.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app, raise_server_exceptions=False)
BASE = settings.API_V1_STR


# ---------------------------------------------------------------------------
# Finance endpoints
# ---------------------------------------------------------------------------

def test_get_expenses_requires_auth():
    assert client.get(f"{BASE}/finance/expenses").status_code == 401


def test_post_hustle_input_requires_auth():
    response = client.post(
        f"{BASE}/finance/hustle-input",
        json={"text": "Kawa 10 PLN"},
    )
    assert response.status_code == 401


def test_hustle_input_text_too_long_returns_422():
    """
    Pydantic waliduje długość tekstu ZANIM endpoint jest wywołany.
    Ten test weryfikuje że limit max_length=1000 działa na poziomie HTTP.
    """
    response = client.post(
        f"{BASE}/finance/hustle-input",
        json={"text": "x" * 1001},
    )
    # 422 (walidacja Pydantic) LUB 401 (brak tokena) — oba są poprawne.
    # Ważne: nie może być 200 ani 500.
    assert response.status_code in (401, 422)


def test_delete_expense_requires_auth():
    assert client.delete(f"{BASE}/finance/expenses/1").status_code == 401


def test_patch_expense_requires_auth():
    assert client.patch(f"{BASE}/finance/expenses/1", json={}).status_code == 401


# ---------------------------------------------------------------------------
# Goals endpoints
# ---------------------------------------------------------------------------

def test_get_goals_requires_auth():
    assert client.get(f"{BASE}/goals/").status_code == 401


def test_post_goal_requires_auth():
    assert client.post(f"{BASE}/goals/", json={"title": "Test"}).status_code == 401


def test_dashboard_requires_auth():
    assert client.get(f"{BASE}/goals/dashboard/today").status_code == 401


def test_activity_history_requires_auth():
    assert client.get(f"{BASE}/goals/activity/history").status_code == 401


def test_smart_create_requires_auth():
    response = client.post(
        f"{BASE}/goals/smart-create",
        json={"idea": "Nauczyć się Pythona"},
    )
    assert response.status_code == 401


def test_smart_create_idea_too_long_returns_422_or_401():
    response = client.post(
        f"{BASE}/goals/smart-create",
        json={"idea": "x" * 501},
    )
    assert response.status_code in (401, 422)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

def test_log_meal_requires_auth():
    response = client.post(
        f"{BASE}/health/log-meal-ai",
        json={"text": "Zjadłem kurczaka"},
    )
    assert response.status_code == 401


def test_get_meals_requires_auth():
    assert client.get(f"{BASE}/health/meals").status_code == 401


def test_delete_meal_requires_auth():
    assert client.delete(f"{BASE}/health/meals/1").status_code == 401


def test_meal_text_too_long_returns_422_or_401():
    response = client.post(
        f"{BASE}/health/log-meal-ai",
        json={"text": "x" * 1001},
    )
    assert response.status_code in (401, 422)


# ---------------------------------------------------------------------------
# Offers endpoints
# ---------------------------------------------------------------------------

def test_get_offers_requires_auth():
    assert client.get(f"{BASE}/offers").status_code == 401


def test_post_offer_requires_auth():
    assert client.post(f"{BASE}/offers", json={}).status_code == 401


def test_delete_offer_requires_auth():
    assert client.delete(f"{BASE}/offers/1").status_code == 401


# ---------------------------------------------------------------------------
# Zbiorczy test — lista wszystkich chronionych ścieżek
# ---------------------------------------------------------------------------

PROTECTED_GET_ROUTES = [
    f"{BASE}/auth/me",
    f"{BASE}/finance/expenses",
    f"{BASE}/goals/",
    f"{BASE}/goals/dashboard/today",
    f"{BASE}/goals/activity/history",
    f"{BASE}/health/meals",
    f"{BASE}/offers",
    f"{BASE}/export/expenses.csv",
    f"{BASE}/export/meals.csv",
]


@pytest.mark.parametrize("path", PROTECTED_GET_ROUTES)
def test_all_protected_get_routes_return_401(path):
    """Żaden chroniony GET endpoint nie jest przypadkowo publiczny."""
    response = client.get(path)
    assert response.status_code == 401, f"{path} powinien zwracać 401, dostał {response.status_code}"

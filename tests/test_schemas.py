"""
Unit testy schematów Pydantic.

Nie wymagają bazy danych ani HTTP — testują czysto walidację danych
na granicy systemu (zanim request trafi do endpointu).
"""

import pytest
from pydantic import ValidationError

from app.schemas.finance import HustleInputRequest, ExpenseUpdate
from app.schemas.health import MealLogAIRequest
from app.schemas.goal import SmartCreateInput
from app.core.config import Settings


# ---------------------------------------------------------------------------
# HustleInputRequest
# ---------------------------------------------------------------------------

def test_hustle_input_accepts_valid_text():
    req = HustleInputRequest(text="Kupiłem kawę za 15 PLN")
    assert req.text == "Kupiłem kawę za 15 PLN"


def test_hustle_input_accepts_max_length():
    req = HustleInputRequest(text="x" * 1000)
    assert len(req.text) == 1000


def test_hustle_input_rejects_text_over_limit():
    with pytest.raises(ValidationError) as exc_info:
        HustleInputRequest(text="x" * 1001)
    assert "max_length" in str(exc_info.value) or "1000" in str(exc_info.value)


def test_hustle_input_accepts_forced_category():
    req = HustleInputRequest(text="coś", forced_category="INCOME")
    assert req.forced_category == "INCOME"


def test_hustle_input_forced_category_optional():
    req = HustleInputRequest(text="coś")
    assert req.forced_category is None


# ---------------------------------------------------------------------------
# MealLogAIRequest
# ---------------------------------------------------------------------------

def test_meal_input_accepts_valid_text():
    req = MealLogAIRequest(text="Zjadłem kurczaka z ryżem")
    assert req.text == "Zjadłem kurczaka z ryżem"


def test_meal_input_rejects_text_over_limit():
    with pytest.raises(ValidationError):
        MealLogAIRequest(text="x" * 1001)


def test_meal_input_accepts_exactly_1000_chars():
    req = MealLogAIRequest(text="a" * 1000)
    assert len(req.text) == 1000


# ---------------------------------------------------------------------------
# SmartCreateInput
# ---------------------------------------------------------------------------

def test_smart_create_accepts_valid_idea():
    req = SmartCreateInput(idea="Chcę nauczyć się Pythona")
    assert req.idea == "Chcę nauczyć się Pythona"


def test_smart_create_accepts_max_length():
    req = SmartCreateInput(idea="x" * 500)
    assert len(req.idea) == 500


def test_smart_create_rejects_idea_over_limit():
    with pytest.raises(ValidationError):
        SmartCreateInput(idea="x" * 501)


# ---------------------------------------------------------------------------
# ExpenseUpdate
# ---------------------------------------------------------------------------

def test_expense_update_rejects_negative_amount():
    with pytest.raises(ValidationError):
        ExpenseUpdate(amount=-10.0)


def test_expense_update_rejects_zero_amount():
    with pytest.raises(ValidationError):
        ExpenseUpdate(amount=0)


def test_expense_update_accepts_positive_amount():
    update = ExpenseUpdate(amount=99.99)
    assert update.amount == 99.99


def test_expense_update_all_fields_optional():
    update = ExpenseUpdate()
    assert update.amount is None
    assert update.category is None
    assert update.description is None


# ---------------------------------------------------------------------------
# Settings / SECRET_KEY validator
# ---------------------------------------------------------------------------

def test_settings_rejects_short_secret_key():
    with pytest.raises(ValueError):
        Settings(
            DATABASE_URL="postgresql://test:test@localhost/test",
            SECRET_KEY="tooshort",
            GROQ_API_KEY="test-key",
        )


def test_settings_accepts_32_char_secret_key():
    s = Settings(
        DATABASE_URL="postgresql://test:test@localhost/test",
        SECRET_KEY="a" * 32,
        GROQ_API_KEY="test-key",
    )
    assert len(s.SECRET_KEY) == 32

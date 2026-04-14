"""
Konfiguracja pytest.

conftest.py jest ładowany przez pytest PRZED importem jakiegokolwiek pliku testowego.
Dzięki temu ustawiamy zmienne środowiskowe zanim pydantic-settings spróbuje
zwalidować Settings() przy imporcie app.core.config.

Wartości tu ustawione są dummy — używane tylko w testach lokalnych gdy brak .env.
W CI te same wartości są ustawione w sekcji `env:` w ci.yml.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://hustle:hustle@localhost:5432/hustle",
)
os.environ.setdefault(
    "SECRET_KEY",
    "ci-only-key-not-real-this-must-be-32-chars-minimum",
)
os.environ.setdefault("GROQ_API_KEY", "test-groq-api-key-not-real")
os.environ.setdefault("DB_SSL", "false")
os.environ.setdefault("AUTH_COOKIE_SECURE", "false")

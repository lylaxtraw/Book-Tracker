"""Configuration, read from the environment (or a local .env file)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Shown in the header and on the splash screen.
    reader_name: str = "Koy"
    studio_name: str = "CherryStraw"
    dedication: str = "With all my love, L.A."

    # The single password that unlocks the library. Change this before deploying.
    app_password: str = "sharks"

    # Signs the session cookie. Generate with: python -c "import secrets;print(secrets.token_hex(32))"
    secret_key: str = "dev-only-change-me"

    # Days a login stays valid before the app asks again.
    session_days: int = 90

    database_url: str = f"sqlite:///{DATA_DIR / 'library.db'}"

    # Open Library is free and needs no key, but asks that clients identify themselves.
    openlibrary_base: str = "https://openlibrary.org"
    covers_base: str = "https://covers.openlibrary.org"
    user_agent: str = "BookTracker/1.0 (personal library app)"
    request_timeout: float = 12.0

    # Set True only when running behind HTTPS (i.e. once it is deployed).
    secure_cookies: bool = False


@lru_cache
def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()

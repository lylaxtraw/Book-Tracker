"""Application settings, read from the environment (or a local .env file)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Branding shown on the splash screen.
    brand_name: str = "CherryStraw"
    brand_dedication: str = "With all my love, L.A."
    app_title: str = "Bookmark"

    # Where the SQLite file lives. On a host with a mounted volume, point this
    # at the volume (e.g. sqlite:////data/booktracker.db -- note four slashes).
    database_url: str = f"sqlite:///{BASE_DIR / 'booktracker.db'}"

    # Signs the session cookie. MUST be overridden in production.
    secret_key: str = "dev-only-change-me"

    # The single account that uses this instance.
    owner_username: str = "koy"
    # Plain password used to bootstrap the account on first boot. It is hashed
    # immediately and never stored in the database in plain form.
    owner_password: str = "changeme"

    # Set to False when serving over plain HTTP on localhost.
    secure_cookies: bool = True

    session_max_age_days: int = 365

    # Open Library
    openlibrary_base_url: str = "https://openlibrary.org"
    openlibrary_covers_url: str = "https://covers.openlibrary.org"
    openlibrary_timeout: float = 12.0
    openlibrary_user_agent: str = "CherryStrawBookmark/1.0 (personal book tracker)"


@lru_cache
def get_settings() -> Settings:
    return Settings()

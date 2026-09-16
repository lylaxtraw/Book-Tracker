"""Shared test fixtures.

The environment is configured *before* the app package is imported, because
`app.database` builds its engine at import time from the settings object. Doing
this any later would point the tests at the real booktracker.db.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TMP_DIR = Path(tempfile.mkdtemp(prefix="bookmark-tests-"))

os.environ["DATABASE_URL"] = f"sqlite:///{TMP_DIR / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["OWNER_USERNAME"] = "koy"
os.environ["OWNER_PASSWORD"] = "sharkteeth"
# TestClient talks plain HTTP, so a Secure-only cookie would never come back.
os.environ["SECURE_COOKIES"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

TEST_USER = "koy"
TEST_PASSWORD = "sharkteeth"


@pytest.fixture()
def client():
    """A clean database per test. Lifespan recreates the schema and seeds it."""
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def anon(client):
    """An unauthenticated client (same as client, since client starts unsigned)."""
    return client


@pytest.fixture()
def auth(client):
    """A client that has already signed in."""
    response = client.post(
        "/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def tags(auth):
    """Every seeded tag, keyed by its role (reading, finished, owned...)."""
    categories = auth.get("/api/categories").json()
    flat = [t for c in categories for t in c["tags"]]
    return {t["role"]: t for t in flat if t["role"]}


def make_book(auth, title="The Deep", **extra):
    payload = {"title": title, "authors": "A. Diver", **extra}
    response = auth.post("/api/books", json=payload)
    assert response.status_code == 201, response.text
    return response.json()

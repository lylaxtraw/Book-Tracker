"""Shared fixtures.

Every test gets a fresh in-memory database seeded with the preset tags, so tests
never touch data/library.db and never depend on each other's leftovers.
"""

import os
import tempfile

# Must be set before anything under app/ is imported — config reads these at
# import time, and we don't want the real library file involved.
_TMP = tempfile.mkdtemp(prefix="booktracker-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/unused.db"
os.environ["APP_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "test-secret-not-for-real-use"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_presets  # noqa: E402

PASSWORD = "testpass"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, future=True)()
    seed_presets(session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def anon(db):
    """A client with no session cookie."""

    # Must be a generator *function*: FastAPI inspects the callable to decide
    # whether it manages a yielded resource. A lambda returning an iterator
    # would be handed to the route as-is.
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(anon):
    """A signed-in client."""
    response = anon.post("/api/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200
    return anon


@pytest.fixture
def tags(client):
    """Preset tags keyed by name, for readable assertions."""
    return {t["name"]: t for t in client.get("/api/tags").json()}


def make_book(client, **overrides):
    payload = {"title": "The Old Man and the Sea", "author": "Ernest Hemingway"}
    payload.update(overrides)
    response = client.post("/api/books", json=payload)
    assert response.status_code == 201, response.text
    return response.json()

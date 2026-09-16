"""Sign in, sign out, and the wall around everything else."""

from conftest import TEST_PASSWORD, TEST_USER


def test_session_starts_signed_out(client):
    body = client.get("/api/auth/session").json()
    assert body["authenticated"] is False
    assert body["username"] is None


def test_health_is_open(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_library_is_closed_to_strangers(client):
    assert client.get("/api/books").status_code == 401
    assert client.get("/api/tags").status_code == 401
    assert client.get("/api/stats").status_code == 401


def test_login_rejects_a_wrong_password(client):
    response = client.post(
        "/api/auth/login", json={"username": TEST_USER, "password": "not-it"}
    )
    assert response.status_code == 401


def test_login_rejects_an_unknown_name(client):
    response = client.post(
        "/api/auth/login", json={"username": "nobody", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401


def test_login_is_case_insensitive_on_the_name(client):
    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USER.upper(), "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["username"] == TEST_USER


def test_signing_in_opens_the_library(auth):
    assert auth.get("/api/auth/session").json()["authenticated"] is True
    assert auth.get("/api/books").status_code == 200


def test_logout_closes_it_again(auth):
    assert auth.post("/api/auth/logout").status_code == 204
    assert auth.get("/api/books").status_code == 401


def test_password_change_needs_the_old_one(auth):
    response = auth.post(
        "/api/auth/password",
        json={"current_password": "wrong", "new_password": "a-longer-one"},
    )
    assert response.status_code == 400


def test_password_change_takes_effect(auth):
    assert (
        auth.post(
            "/api/auth/password",
            json={"current_password": TEST_PASSWORD, "new_password": "chandelure-77"},
        ).status_code
        == 204
    )
    auth.post("/api/auth/logout")

    assert (
        auth.post(
            "/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD}
        ).status_code
        == 401
    )
    assert (
        auth.post(
            "/api/auth/login",
            json={"username": TEST_USER, "password": "chandelure-77"},
        ).status_code
        == 200
    )


def test_short_passwords_are_refused(auth):
    response = auth.post(
        "/api/auth/password",
        json={"current_password": TEST_PASSWORD, "new_password": "short"},
    )
    assert response.status_code == 422


def test_the_password_is_never_stored_in_the_clear(auth):
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        user = db.query(User).one()
        assert TEST_PASSWORD not in user.password_hash
        assert user.password_hash.startswith("$argon2")
    finally:
        db.close()

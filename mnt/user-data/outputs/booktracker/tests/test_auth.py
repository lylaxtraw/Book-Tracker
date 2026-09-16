from .conftest import PASSWORD


def test_library_is_locked_without_a_session(anon):
    assert anon.get("/api/books").status_code == 401
    assert anon.get("/api/tags").status_code == 401
    assert anon.get("/api/stats").status_code == 401


def test_wrong_password_is_rejected(anon):
    response = anon.post("/api/auth/login", json={"password": "sharks"})
    assert response.status_code == 401
    assert "match" in response.json()["detail"].lower()


def test_login_opens_the_library(anon):
    assert anon.post("/api/auth/login", json={"password": PASSWORD}).status_code == 200
    assert anon.get("/api/books").status_code == 200
    assert anon.get("/api/auth/session").json()["signed_in"] is True


def test_logout_closes_it_again(client):
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/books").status_code == 401


def test_session_endpoint_is_public_and_carries_the_splash_text(anon):
    body = anon.get("/api/auth/session").json()
    assert body["signed_in"] is False
    assert body["studio_name"]
    assert body["dedication"]


def test_health_needs_no_session(anon):
    assert anon.get("/api/health").json()["ok"] is True

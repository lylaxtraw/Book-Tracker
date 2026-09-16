"""A deliberately small auth layer.

One reader, one password. Logging in signs a timestamped token and drops it in an
HttpOnly cookie, so the phone stays logged in for `session_days` and nobody who
stumbles onto the URL can read the library.
"""

import hmac

from fastapi import Cookie, HTTPException, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import get_settings

COOKIE_NAME = "bt_session"
_SALT = "book-tracker-session"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt=_SALT)


def password_matches(candidate: str) -> bool:
    """Constant-time compare, so the password can't be guessed by timing."""
    return hmac.compare_digest(candidate, get_settings().app_password)


def issue_session(response: Response) -> None:
    settings = get_settings()
    token = _serializer().dumps({"reader": settings.reader_name})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def session_is_valid(token: str | None) -> bool:
    if not token:
        return False
    max_age = get_settings().session_days * 24 * 3600
    try:
        _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return False
    return True


def require_auth(bt_session: str | None = Cookie(default=None)) -> None:
    """FastAPI dependency. Guards every /api route except login and health."""
    if not session_is_valid(bt_session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue"
        )

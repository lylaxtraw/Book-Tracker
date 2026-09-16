"""Password hashing and the session dependency guarding the API."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

_hasher = PasswordHasher()

SESSION_KEY = "uid"


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, plain)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hashed)
    except InvalidHashError:
        return True


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = (
        db.query(User).filter(User.username == username.strip().lower()).one_or_none()
    )
    if user is None:
        # Hash anyway so a missing user and a wrong password take similar time.
        _hasher.hash(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Raise 401 unless the request carries a valid signed session cookie."""
    uid = request.session.get(SESSION_KEY)
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in."
        )
    user = db.get(User, uid)
    if user is None:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session no longer valid."
        )
    return user

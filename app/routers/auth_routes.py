"""Sign in, sign out, and change the password."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import (
    SESSION_KEY,
    authenticate,
    current_user,
    hash_password,
    verify_password,
)
from ..database import get_db
from ..models import User, Book, Tag, TagCategory, Preference, ReadingGoal
from ..schemas import LoginRequest, PasswordChangeRequest, UsernameChangeRequest, SessionInfo
from ..seed import seed_all

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/session", response_model=SessionInfo)
def read_session(request: Request, db: Session = Depends(get_db)) -> SessionInfo:
    uid = request.session.get(SESSION_KEY)
    if uid is None:
        return SessionInfo(authenticated=False)
    user = db.get(User, uid)
    if user is None:
        request.session.clear()
        return SessionInfo(authenticated=False)
    return SessionInfo(authenticated=True, username=user.username)


@router.post("/login", response_model=SessionInfo)
def login(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> SessionInfo:
    user = authenticate(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That username and password do not match.",
        )
    request.session[SESSION_KEY] = user.id
    return SessionInfo(authenticated=True, username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def logout(request: Request) -> None:
    request.session.clear()


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is not right.",
        )
    user.password_hash = hash_password(payload.new_password)
    db.commit()


@router.post("/username", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def change_username(
    payload: UsernameChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is not right.",
        )
    # Check if username already exists
    existing = db.query(User).filter(User.username == payload.new_username).first()
    if existing and existing.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That username is already taken.",
        )
    user.username = payload.new_username
    db.commit()


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def reset_database(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    """Reset the entire library to a clean state.
    
    Deletes all books, tags, categories, preferences, and reading goals,
    then reinitializes with seed data.
    """
    # Delete in order to respect foreign key constraints
    db.query(Book).delete()
    db.query(ReadingGoal).delete()
    db.query(Tag).delete()
    db.query(TagCategory).delete()
    db.query(Preference).delete()
    db.commit()
    
    # Reseed the data
    seed_all(db)

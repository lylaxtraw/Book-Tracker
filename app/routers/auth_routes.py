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
from ..models import User
from ..schemas import LoginRequest, PasswordChangeRequest, SessionInfo

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

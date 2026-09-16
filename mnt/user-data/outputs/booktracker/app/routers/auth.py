from fastapi import APIRouter, Cookie, HTTPException, Response, status

from ..auth import clear_session, issue_session, password_matches, session_is_valid
from ..config import get_settings
from ..schemas import LoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/session")
def read_session(bt_session: str | None = Cookie(default=None)) -> dict:
    settings = get_settings()
    return {
        "signed_in": session_is_valid(bt_session),
        "reader_name": settings.reader_name,
        "studio_name": settings.studio_name,
        "dedication": settings.dedication,
    }


@router.post("/login")
def login(payload: LoginIn, response: Response) -> dict:
    if not password_matches(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That password doesn't match. Try again.",
        )
    issue_session(response)
    return {"signed_in": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    clear_session(response)
    return {"signed_in": False}

"""Application entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import __version__
from .config import STATIC_DIR, get_settings
from .database import Base, SessionLocal, engine
from .routers import auth_routes, backup, books, search, stats, tags
from .seed import seed_all


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
    yield


settings = get_settings()

app = FastAPI(
    title=f"{settings.brand_name} {settings.app_title}",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="bookmark_session",
    max_age=settings.session_max_age_days * 24 * 60 * 60,
    same_site="lax",
    https_only=settings.secure_cookies,
)

for module in (auth_routes, books, tags, search, stats, backup):
    app.include_router(module.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/branding")
def branding() -> dict[str, str]:
    """The splash screen reads its text from here, so it lives in one place."""
    return {
        "brand": settings.brand_name,
        "dedication": settings.brand_dedication,
        "title": settings.app_title,
    }


# Static assets. mounted last so /api/* wins any name collision.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json"
    )


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    """Must be served from the root so it can control the whole scope."""
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/", include_in_schema=False, response_model=None)
@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def spa(full_path: str = "") -> FileResponse | JSONResponse:
    """Hand every non-API path to the single-page app."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found."}, status_code=404)
    return FileResponse(STATIC_DIR / "index.html")


@app.exception_handler(404)
async def not_found(request: Request, _exc) -> FileResponse | JSONResponse:
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found."}, status_code=404)
    return FileResponse(STATIC_DIR / "index.html")

"""Application entrypoint.

Run it with:  uvicorn app.main:app --reload
Then open:    http://127.0.0.1:8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import auth, books, search, stats, tags, transfer
from .seed import seed_presets

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_presets(db)
    yield


app = FastAPI(
    title="Book Tracker",
    description="A personal library, kept properly.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(tags.router)
app.include_router(books.router)
app.include_router(search.router)
app.include_router(stats.router)
app.include_router(transfer.router)


@app.get("/api/health", include_in_schema=False)
def health() -> dict:
    return {"ok": True, "reader": get_settings().reader_name}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Service worker must be served from the root to control the whole scope.
@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json"
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

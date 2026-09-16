"""Import and export — the escape hatch.

The library is Koy's, so it has to be possible to walk out with it. CSV opens in
Numbers or Excel; the JSON backup round-trips everything including tag colours.
"""

import csv
import io
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import Book, Category, Goal, Tag
from ..seed import custom_category_id

router = APIRouter(
    prefix="/api", tags=["transfer"], dependencies=[Depends(require_auth)]
)

CSV_COLUMNS = [
    "title",
    "author",
    "isbn",
    "publisher",
    "year",
    "pages",
    "rating",
    "progress_pages",
    "started_on",
    "finished_on",
    "tags",
    "notes",
    "cover_url",
]


def _parse_date(value: str | None) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    value = (value or "").strip()
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_float(value: str | None) -> float | None:
    value = (value or "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tag_by_name(db: Session, name: str) -> Tag:
    """Find a tag by name, case-insensitively, creating it if it's new."""
    name = name.strip()
    existing = db.query(Tag).filter(Tag.name.ilike(name)).first() if name else None
    if existing:
        return existing
    tag = Tag(name=name, color="#A472F0", category_id=custom_category_id(db))
    db.add(tag)
    db.flush()
    return tag


# ----------------------------------------------------------------------- export


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_db)):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()

    for book in db.query(Book).order_by(Book.title).all():
        writer.writerow(
            {
                "title": book.title,
                "author": book.author or "",
                "isbn": book.isbn or "",
                "publisher": book.publisher or "",
                "year": book.year or "",
                "pages": book.pages or "",
                "rating": book.rating or "",
                "progress_pages": book.progress_pages,
                "started_on": book.started_on.isoformat() if book.started_on else "",
                "finished_on": book.finished_on.isoformat() if book.finished_on else "",
                "tags": "; ".join(t.name for t in book.tags),
                "notes": book.notes or "",
                "cover_url": book.cover_url or "",
            }
        )

    buffer.seek(0)
    stamp = date.today().isoformat()
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="library-{stamp}.csv"'
        },
    )


@router.get("/backup.json")
def export_backup(db: Session = Depends(get_db)):
    payload = {
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "categories": [
            {
                "name": c.name,
                "exclusive": c.exclusive,
                "is_preset": c.is_preset,
                "position": c.position,
            }
            for c in db.query(Category).order_by(Category.position).all()
        ],
        "tags": [
            {
                "name": t.name,
                "color": t.color,
                "category": t.category.name,
                "is_preset": t.is_preset,
                "position": t.position,
            }
            for t in db.query(Tag).all()
        ],
        "books": [
            {
                "title": b.title,
                "author": b.author,
                "isbn": b.isbn,
                "publisher": b.publisher,
                "year": b.year,
                "pages": b.pages,
                "cover_url": b.cover_url,
                "openlibrary_key": b.openlibrary_key,
                "description": b.description,
                "rating": b.rating,
                "notes": b.notes,
                "progress_pages": b.progress_pages,
                "started_on": b.started_on.isoformat() if b.started_on else None,
                "finished_on": b.finished_on.isoformat() if b.finished_on else None,
                "tags": [t.name for t in b.tags],
            }
            for b in db.query(Book).order_by(Book.id).all()
        ],
        "goals": [
            {"year": g.year, "target_books": g.target_books}
            for g in db.query(Goal).all()
        ],
    }
    stamp = date.today().isoformat()
    return StreamingResponse(
        iter([json.dumps(payload, indent=2, ensure_ascii=False)]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="library-backup-{stamp}.json"'
        },
    )


# ----------------------------------------------------------------------- import


@router.post("/import.csv")
async def import_csv(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))

    if not reader.fieldnames or "title" not in {
        (f or "").strip().lower() for f in reader.fieldnames
    }:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That file needs a column called “title”. Export one first to see the format.",
        )

    added = skipped = 0
    for row in reader:
        row = {(k or "").strip().lower(): v for k, v in row.items()}
        title = (row.get("title") or "").strip()
        if not title:
            skipped += 1
            continue

        author = (row.get("author") or "").strip() or None
        duplicate = (
            db.query(Book)
            .filter(Book.title.ilike(title))
            .filter(Book.author.ilike(author) if author else Book.author.is_(None))
            .one_or_none()
        )
        if duplicate:
            skipped += 1
            continue

        book = Book(
            title=title,
            author=author,
            isbn=(row.get("isbn") or "").strip() or None,
            publisher=(row.get("publisher") or "").strip() or None,
            year=_parse_int(row.get("year")),
            pages=_parse_int(row.get("pages")),
            rating=_parse_float(row.get("rating")),
            notes=(row.get("notes") or "").strip() or None,
            cover_url=(row.get("cover_url") or "").strip() or None,
            progress_pages=_parse_int(row.get("progress_pages")) or 0,
            started_on=_parse_date(row.get("started_on")),
            finished_on=_parse_date(row.get("finished_on")),
        )

        names = [n.strip() for n in (row.get("tags") or "").split(";") if n.strip()]
        book.tags = [_tag_by_name(db, n) for n in names]

        db.add(book)
        added += 1

    db.commit()
    return {"added": added, "skipped": skipped}

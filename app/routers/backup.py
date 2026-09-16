"""Import, export and interface preferences.

Export is deliberately plain CSV so the file opens in Numbers or Excel without
ceremony, and a JSON backup exists for round-tripping the whole library --
books, tags, categories and goals -- into a fresh instance.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Book, Preference, ReadingGoal, Tag, TagCategory
from ..schemas import ImportReport, PreferenceIn

router = APIRouter(
    prefix="/api", tags=["backup"], dependencies=[Depends(current_user)]
)

CSV_COLUMNS = [
    "title",
    "subtitle",
    "authors",
    "series",
    "publisher",
    "published_year",
    "page_count",
    "isbn10",
    "isbn13",
    "language",
    "rating",
    "current_page",
    "date_started",
    "date_finished",
    "tags",
    "notes",
    "cover_url",
    "openlibrary_key",
]

# Column names other trackers use, mapped onto ours.
ALIASES = {
    "book title": "title",
    "author": "authors",
    "author l-f": "authors",
    "isbn": "isbn10",
    "isbn13": "isbn13",
    "my rating": "rating",
    "number of pages": "page_count",
    "year published": "published_year",
    "original publication year": "published_year",
    "date read": "date_finished",
    "my review": "notes",
    "bookshelves": "tags",
    "exclusive shelf": "tags",
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            return parsed
        except ValueError:
            continue
    return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def _parse_float(value: str | None) -> float | None:
    """Ratings, snapped to the nearest half star and clamped to 0-5.

    Other trackers use scales we do not, and a stray 3.7 would pass the import
    but then fail validation on the way back out.
    """
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return min(round(number * 2) / 2, 5.0)


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()

    for book in db.query(Book).order_by(Book.title).all():
        writer.writerow(
            {
                "title": book.title,
                "subtitle": book.subtitle or "",
                "authors": book.authors or "",
                "series": book.series or "",
                "publisher": book.publisher or "",
                "published_year": book.published_year or "",
                "page_count": book.page_count or "",
                "isbn10": book.isbn10 or "",
                "isbn13": book.isbn13 or "",
                "language": book.language or "",
                "rating": book.rating if book.rating is not None else "",
                "current_page": book.current_page or 0,
                "date_started": book.date_started or "",
                "date_finished": book.date_finished or "",
                "tags": "; ".join(t.name for t in book.tags),
                "notes": book.notes or "",
                "cover_url": book.cover_url or "",
                "openlibrary_key": book.openlibrary_key or "",
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


@router.get("/export/json")
def export_json(db: Session = Depends(get_db)) -> StreamingResponse:
    payload = {
        "exported_at": datetime.now().isoformat(),
        "version": 1,
        "categories": [
            {
                "name": c.name,
                "description": c.description,
                "position": c.position,
                "exclusive": c.exclusive,
                "tags": [
                    {
                        "name": t.name,
                        "color": t.color,
                        "icon": t.icon,
                        "role": t.role,
                        "position": t.position,
                    }
                    for t in c.tags
                ],
            }
            for c in db.query(TagCategory).order_by(TagCategory.position).all()
        ],
        "books": [
            {
                "title": b.title,
                "subtitle": b.subtitle,
                "authors": b.authors,
                "series": b.series,
                "publisher": b.publisher,
                "published_year": b.published_year,
                "page_count": b.page_count,
                "isbn10": b.isbn10,
                "isbn13": b.isbn13,
                "language": b.language,
                "cover_url": b.cover_url,
                "description": b.description,
                "rating": b.rating,
                "notes": b.notes,
                "current_page": b.current_page,
                "date_started": b.date_started.isoformat() if b.date_started else None,
                "date_finished": (
                    b.date_finished.isoformat() if b.date_finished else None
                ),
                "openlibrary_key": b.openlibrary_key,
                "source": b.source,
                "tags": [t.name for t in b.tags],
            }
            for b in db.query(Book).order_by(Book.id).all()
        ],
        "goals": [
            {
                "year": g.year,
                "target_books": g.target_books,
                "target_pages": g.target_pages,
            }
            for g in db.query(ReadingGoal).all()
        ],
        "preferences": {p.key: p.value for p in db.query(Preference).all()},
    }

    stamp = date.today().isoformat()
    return StreamingResponse(
        iter([json.dumps(payload, indent=2, ensure_ascii=False)]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="backup-{stamp}.json"'
        },
    )


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


def _tag_by_name(db: Session, name: str, cache: dict[str, Tag]) -> Tag | None:
    key = name.strip().lower()
    if not key:
        return None
    if key in cache:
        return cache[key]
    tag = db.query(Tag).filter(func.lower(Tag.name) == key).one_or_none()
    if tag is None:
        # Land unknown tags in an 'Imported' category rather than dropping them.
        category = (
            db.query(TagCategory)
            .filter(func.lower(TagCategory.name) == "imported")
            .one_or_none()
        )
        if category is None:
            category = TagCategory(
                name="Imported",
                description="Tags that arrived with an import.",
                position=99,
                exclusive=False,
            )
            db.add(category)
            db.flush()
        tag = Tag(
            name=name.strip(),
            color="#4ea8ff",
            position=0,
            category_id=category.id,
            is_preset=False,
        )
        db.add(tag)
        db.flush()
    cache[key] = tag
    return tag


@router.post("/import/csv", response_model=ImportReport)
async def import_csv(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> ImportReport:
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="That file has no header row."
        )

    created = skipped = 0
    errors: list[str] = []
    tag_cache: dict[str, Tag] = {}

    for line_no, raw_row in enumerate(reader, start=2):
        row: dict[str, str] = {}
        for key, value in raw_row.items():
            if key is None:
                continue
            clean = key.strip().lower()
            row[ALIASES.get(clean, clean)] = (value or "").strip()

        title = row.get("title", "").strip()
        if not title:
            skipped += 1
            continue

        isbn13 = row.get("isbn13") or None
        duplicate = None
        if isbn13:
            duplicate = db.query(Book).filter(Book.isbn13 == isbn13).first()
        if duplicate is None:
            duplicate = (
                db.query(Book)
                .filter(
                    func.lower(Book.title) == title.lower(),
                    func.lower(func.coalesce(Book.authors, ""))
                    == row.get("authors", "").lower(),
                )
                .first()
            )
        if duplicate is not None:
            skipped += 1
            continue

        try:
            book = Book(
                title=title[:500],
                subtitle=(row.get("subtitle") or None),
                authors=(row.get("authors") or None),
                series=(row.get("series") or None),
                publisher=(row.get("publisher") or None),
                published_year=_parse_int(row.get("published_year")),
                page_count=min(_parse_int(row.get("page_count")) or 0, 100_000) or None,
                isbn10=(row.get("isbn10") or None),
                isbn13=isbn13,
                language=(row.get("language") or None),
                cover_url=(row.get("cover_url") or None),
                notes=(row.get("notes") or None),
                rating=_parse_float(row.get("rating")),
                current_page=_parse_int(row.get("current_page")) or 0,
                date_started=_parse_date(row.get("date_started")),
                date_finished=_parse_date(row.get("date_finished")),
                openlibrary_key=(row.get("openlibrary_key") or None),
                source="import",
            )

            tag_names = [
                part
                for chunk in (row.get("tags") or "").replace(",", ";").split(";")
                if (part := chunk.strip())
            ]
            tags = [t for name in tag_names if (t := _tag_by_name(db, name, tag_cache))]
            book.tags = list({t.id: t for t in tags}.values())

            db.add(book)
            created += 1
        except Exception as exc:  # noqa: BLE001 - report, don't abort the whole file
            skipped += 1
            if len(errors) < 25:
                errors.append(f"Row {line_no}: {exc}")

    db.commit()
    return ImportReport(created=created, skipped=skipped, errors=errors)


# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------


@router.get("/preferences", response_model=dict[str, str])
def read_preferences(db: Session = Depends(get_db)) -> dict[str, str]:
    return {p.key: p.value for p in db.query(Preference).all()}


@router.put("/preferences/{key}", response_model=dict[str, str])
def write_preference(
    key: str, payload: PreferenceIn, db: Session = Depends(get_db)
) -> dict[str, str]:
    pref = db.get(Preference, key)
    if pref is None:
        pref = Preference(key=key, value=payload.value)
        db.add(pref)
    else:
        pref.value = payload.value
    db.commit()
    return {key: payload.value}

"""Everything that happens to a book after it is in the library."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Book, Tag, TagCategory, book_tags
from ..schemas import BookCreate, BookOut, BookPage, BookUpdate, TagOut

router = APIRouter(
    prefix="/api/books", tags=["books"], dependencies=[Depends(current_user)]
)

SORTS = {
    "recent": (Book.created_at.desc(),),
    "updated": (Book.updated_at.desc(),),
    "title": (func.lower(Book.title).asc(),),
    "author": (func.lower(Book.authors).asc(), func.lower(Book.title).asc()),
    "rating": (Book.rating.desc().nullslast(), func.lower(Book.title).asc()),
    "year": (Book.published_year.desc().nullslast(),),
    "pages": (Book.page_count.desc().nullslast(),),
    "finished": (Book.date_finished.desc().nullslast(),),
}


def resolve_tags(db: Session, tag_ids: list[int]) -> list[Tag]:
    """Load tags by id, rejecting unknown ids and exclusivity violations."""
    if not tag_ids:
        return []

    unique_ids = list(dict.fromkeys(tag_ids))
    tags = db.query(Tag).filter(Tag.id.in_(unique_ids)).all()

    found = {t.id for t in tags}
    missing = [i for i in unique_ids if i not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown tag ids: {missing}"
        )

    # An exclusive category accepts at most one of its tags per book.
    by_category: dict[int, list[Tag]] = {}
    for tag in tags:
        by_category.setdefault(tag.category_id, []).append(tag)

    for category_id, group in by_category.items():
        if len(group) < 2:
            continue
        category = db.get(TagCategory, category_id)
        if category is not None and category.exclusive:
            names = ", ".join(sorted(t.name for t in group))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"'{category.name}' only allows one tag per book, "
                    f"but you sent: {names}."
                ),
            )

    return tags


def apply_role_side_effects(book: Book, tags: list[Tag]) -> None:
    """Fill in dates the reader would otherwise have to type.

    Tagging something 'Reading' stamps a start date; tagging it 'Read' stamps a
    finish date and pins the progress bar to full. Both only fire when the
    field is still empty, so a date the reader set by hand is never overwritten.
    """
    roles = {t.role for t in tags if t.role}
    today = date.today()

    if "reading" in roles and book.date_started is None:
        book.date_started = today

    if "finished" in roles:
        if book.date_finished is None:
            book.date_finished = today
        if book.page_count:
            book.current_page = book.page_count
    elif roles & {"reading", "wishlist"} and book.date_finished is not None:
        # An explicit move backwards ('Read' -> 'Reading'). Only these two
        # roles clear the date; an untagged book keeps whatever was typed.
        book.date_finished = None


def to_out(book: Book) -> BookOut:
    return BookOut(
        id=book.id,
        title=book.title,
        subtitle=book.subtitle,
        authors=book.authors,
        series=book.series,
        publisher=book.publisher,
        published_year=book.published_year,
        page_count=book.page_count,
        isbn10=book.isbn10,
        isbn13=book.isbn13,
        language=book.language,
        cover_url=book.cover_url,
        description=book.description,
        rating=book.rating,
        notes=book.notes,
        current_page=book.current_page,
        date_started=book.date_started,
        date_finished=book.date_finished,
        openlibrary_key=book.openlibrary_key,
        source=book.source,
        progress_percent=book.progress_percent,
        created_at=book.created_at,
        updated_at=book.updated_at,
        tags=[
            TagOut(
                id=t.id,
                name=t.name,
                color=t.color,
                icon=t.icon,
                role=t.role,
                position=t.position,
                category_id=t.category_id,
                is_preset=t.is_preset,
            )
            for t in sorted(book.tags, key=lambda t: (t.category_id, t.position))
        ],
    )


@router.get("", response_model=BookPage)
def list_books(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Free text over title/author"),
    tag_ids: list[int] = Query(default=[]),
    match: str = Query(default="any", pattern="^(any|all)$"),
    untagged: bool = False,
    min_rating: float | None = Query(default=None, ge=0, le=5),
    sort: str = Query(default="recent"),
    limit: int = Query(default=60, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> BookPage:
    query = db.query(Book)

    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Book.title).like(needle),
                func.lower(Book.authors).like(needle),
                func.lower(Book.series).like(needle),
                func.lower(Book.publisher).like(needle),
                Book.isbn13.like(needle),
                Book.isbn10.like(needle),
            )
        )

    if min_rating is not None:
        query = query.filter(Book.rating >= min_rating)

    if untagged:
        query = query.filter(~Book.tags.any())
    elif tag_ids:
        if match == "all":
            # Every requested tag must be present.
            sub = (
                select(book_tags.c.book_id)
                .where(book_tags.c.tag_id.in_(tag_ids))
                .group_by(book_tags.c.book_id)
                .having(func.count(func.distinct(book_tags.c.tag_id)) == len(set(tag_ids)))
            )
            query = query.filter(Book.id.in_(sub))
        else:
            query = query.filter(Book.tags.any(Tag.id.in_(tag_ids)))

    total = query.with_entities(func.count(func.distinct(Book.id))).scalar() or 0

    order_by = SORTS.get(sort, SORTS["recent"])
    books = query.order_by(*order_by).offset(offset).limit(limit).all()

    return BookPage(
        items=[to_out(b) for b in books], total=total, limit=limit, offset=offset
    )


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookOut:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found.")
    return to_out(book)


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, db: Session = Depends(get_db)) -> BookOut:
    data = payload.model_dump(exclude={"tag_ids"})
    book = Book(**data)
    book.tags = resolve_tags(db, payload.tag_ids)
    apply_role_side_effects(book, book.tags)
    db.add(book)
    db.commit()
    db.refresh(book)
    return to_out(book)


@router.patch("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int, payload: BookUpdate, db: Session = Depends(get_db)
) -> BookOut:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found.")

    data = payload.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)

    for field, value in data.items():
        setattr(book, field, value)

    if tag_ids is not None:
        book.tags = resolve_tags(db, tag_ids)
        apply_role_side_effects(book, book.tags)

    if book.page_count and book.current_page > book.page_count:
        book.current_page = book.page_count

    db.commit()
    db.refresh(book)
    return to_out(book)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_book(book_id: int, db: Session = Depends(get_db)) -> None:
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found.")
    db.delete(book)
    db.commit()


@router.post("/{book_id}/progress", response_model=BookOut)
def set_progress(
    book_id: int,
    current_page: int = Query(ge=0),
    db: Session = Depends(get_db),
) -> BookOut:
    """A one-tap endpoint for the progress slider on the book card."""
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found.")
    if book.page_count:
        current_page = min(current_page, book.page_count)
    book.current_page = current_page
    db.commit()
    db.refresh(book)
    return to_out(book)

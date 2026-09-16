from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import Book, Tag
from ..schemas import BookIn, BookOut, BookPatch

router = APIRouter(
    prefix="/api/books", tags=["books"], dependencies=[Depends(require_auth)]
)

SORTS = {
    "added": Book.added_at.desc(),
    "title": Book.title.asc(),
    "author": Book.author.asc(),
    "year": Book.year.desc(),
    "rating": Book.rating.desc(),
    "finished": Book.finished_on.desc(),
}


def resolve_tags(db: Session, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    tags = db.query(Tag).filter(Tag.id.in_(set(tag_ids))).all()
    missing = set(tag_ids) - {t.id for t in tags}
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown tag id(s): {', '.join(str(m) for m in sorted(missing))}",
        )
    return tags


def enforce_exclusive(tags: list[Tag]) -> list[Tag]:
    """Keep only the last tag chosen from each exclusive category.

    This is what makes marking a book "Read" quietly drop "Reading" instead of
    leaving both stuck on the cover.
    """
    kept: dict[int, Tag] = {}
    loose: list[Tag] = []
    for tag in tags:
        if tag.category and tag.category.exclusive:
            kept[tag.category_id] = tag
        else:
            loose.append(tag)
    return loose + list(kept.values())


def apply_side_effects(book: Book) -> None:
    """Small conveniences so the dates and progress stay honest."""
    if book.finished_on and book.pages:
        book.progress_pages = book.pages
    if book.pages and book.progress_pages > book.pages:
        book.progress_pages = book.pages
    if book.progress_pages > 0 and book.started_on is None:
        book.started_on = date.today()


@router.get("", response_model=list[BookOut])
def list_books(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Matches title, author or ISBN"),
    tag: list[int] | None = Query(default=None, description="Repeatable tag id"),
    match: str = Query(default="any", pattern="^(any|all)$"),
    sort: str = Query(default="added"),
):
    query = db.query(Book)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like))
        )

    if tag:
        wanted = set(tag)
        if match == "all":
            for tag_id in wanted:
                query = query.filter(Book.tags.any(Tag.id == tag_id))
        else:
            query = query.filter(Book.tags.any(Tag.id.in_(wanted)))

    return query.order_by(SORTS.get(sort, SORTS["added"])).all()


@router.get("/{book_id}", response_model=BookOut)
def read_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No book with that id")
    return book


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookIn, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"tag_ids"})
    book = Book(**data)
    book.tags = enforce_exclusive(resolve_tags(db, payload.tag_ids))
    apply_side_effects(book)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.patch("/{book_id}", response_model=BookOut)
def update_book(book_id: int, payload: BookPatch, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No book with that id")

    data = payload.model_dump(exclude_unset=True)
    tag_ids = data.pop("tag_ids", None)

    for field, value in data.items():
        setattr(book, field, value)

    if tag_ids is not None:
        book.tags = enforce_exclusive(resolve_tags(db, tag_ids))

    apply_side_effects(book)
    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No book with that id")
    db.delete(book)
    db.commit()

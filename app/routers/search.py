"""Look a book up instead of typing it out.

Two doors into the same room:

  GET  /api/search/quick     one box, the way most lookups start
  POST /api/search/advanced  the drop-down panel, several fields at once

Both return scored candidates with `best_match` singled out, which is what the
confirm-or-deny card in the interface is built on.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import openlibrary
from ..auth import current_user
from ..database import get_db
from ..models import Book
from ..schemas import AdvancedSearchQuery, BookCandidate, BookOut, SearchResults
from .books import apply_role_side_effects, resolve_tags, to_out

router = APIRouter(
    prefix="/api/search", tags=["search"], dependencies=[Depends(current_user)]
)


@router.get("/quick", response_model=SearchResults)
async def quick_search(
    q: str = Query(min_length=1, max_length=300),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResults:
    return await openlibrary.search(AdvancedSearchQuery(q=q, limit=limit))


@router.post("/advanced", response_model=SearchResults)
async def advanced_search(query: AdvancedSearchQuery) -> SearchResults:
    if query.is_empty():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fill in at least one field to search.",
        )
    return await openlibrary.search(query)


@router.post("/confirm", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def confirm_candidate(
    candidate: BookCandidate,
    tag_ids: list[int] = Query(default=[]),
    db: Session = Depends(get_db),
) -> BookOut:
    """'Yes, that's the one.' Turn a search hit into a book on the shelf."""
    if candidate.openlibrary_key:
        existing = (
            db.query(Book)
            .filter(Book.openlibrary_key == candidate.openlibrary_key)
            .one_or_none()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{existing.title}' is already in your library.",
            )

    book = Book(
        title=candidate.title,
        subtitle=candidate.subtitle,
        authors=candidate.authors,
        publisher=candidate.publisher,
        published_year=candidate.published_year,
        page_count=candidate.page_count,
        isbn10=candidate.isbn10,
        isbn13=candidate.isbn13,
        language=candidate.language,
        cover_url=candidate.cover_url,
        openlibrary_key=candidate.openlibrary_key,
        source="openlibrary",
    )
    book.tags = resolve_tags(db, tag_ids)
    apply_role_side_effects(book, book.tags)
    db.add(book)
    db.commit()
    db.refresh(book)
    return to_out(book)

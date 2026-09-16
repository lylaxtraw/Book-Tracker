import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import openlibrary
from ..auth import require_auth
from ..schemas import SearchHit

router = APIRouter(
    prefix="/api/search", tags=["search"], dependencies=[Depends(require_auth)]
)


@router.get("", response_model=list[SearchHit])
async def search_catalogue(
    q: str | None = Query(default=None, description="Plain search, any words"),
    title: str | None = None,
    author: str | None = None,
    isbn: str | None = None,
    subject: str | None = None,
    publisher: str | None = None,
    year: int | None = None,
    limit: int = Query(default=12, ge=1, le=50),
):
    """Search Open Library. Every field is optional; send as many as you like."""
    if not any([q, title, author, isbn, subject, publisher, year]):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Fill in at least one field to search"
        )

    try:
        return await openlibrary.search(
            query=q,
            title=title,
            author=author,
            isbn=isbn,
            subject=subject,
            publisher=publisher,
            year=year,
            limit=limit,
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Open Library took too long. Try again, or add the book by hand.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Couldn't reach Open Library. Try again, or add the book by hand.",
        )

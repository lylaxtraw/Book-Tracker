"""Talks to Open Library — the free, key-less catalogue behind the search screen.

Two jobs:
  1. turn a set of fields (title, author, ISBN, subject, year) into one query,
  2. rank what comes back, so the closest match sits at the top and Koy only has
     to confirm it.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

import httpx

from .config import get_settings
from .schemas import SearchHit

FIELDS = ",".join(
    [
        "key",
        "title",
        "author_name",
        "first_publish_year",
        "isbn",
        "cover_i",
        "number_of_pages_median",
        "publisher",
        "edition_count",
    ]
)

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")


def normalise(text: str | None) -> str:
    if not text:
        return ""
    return _SPACE.sub(" ", _PUNCT.sub(" ", text.lower())).strip()


def similarity(a: str | None, b: str | None) -> float:
    a, b = normalise(a), normalise(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def build_params(
    *,
    query: str | None = None,
    title: str | None = None,
    author: str | None = None,
    isbn: str | None = None,
    subject: str | None = None,
    publisher: str | None = None,
    year: int | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """Map the Advanced Search fields onto Open Library's query parameters."""
    params: dict[str, Any] = {"fields": FIELDS, "limit": max(1, min(limit, 50))}

    if isbn:
        params["isbn"] = re.sub(r"[^0-9Xx]", "", isbn)
    if title:
        params["title"] = title
    if author:
        params["author"] = author
    if subject:
        params["subject"] = subject
    if publisher:
        params["publisher"] = publisher
    if year:
        params["first_publish_year"] = year

    # A loose phrase is only sent when no structured field was given, otherwise
    # Open Library treats it as an extra AND and drops good matches.
    structured = {"isbn", "title", "author", "subject", "publisher"} & params.keys()
    if query and not structured:
        params["q"] = query

    return params


def score(doc: dict[str, Any], *, title: str | None, author: str | None) -> int:
    """0–100. Title agreement dominates; author and edition count nudge ties."""
    doc_authors = doc.get("author_name") or []
    if title or author:
        title_part = similarity(title, doc.get("title")) if title else 0.0
        author_part = (
            max((similarity(author, a) for a in doc_authors), default=0.0)
            if author
            else 0.0
        )
        if title and author:
            base = 0.7 * title_part + 0.3 * author_part
        else:
            base = title_part or author_part
    else:
        # Free-text or ISBN search: Open Library's own ordering is the signal.
        base = 0.8

    # Widely-published editions are more likely to be the one on the shelf.
    editions = doc.get("edition_count") or 1
    bonus = min(0.08, (editions - 1) * 0.004)
    return int(round(min(1.0, base + bonus) * 100))


def to_hit(doc: dict[str, Any], *, covers_base: str) -> SearchHit:
    isbns = doc.get("isbn") or []
    cover_id = doc.get("cover_i")
    authors = doc.get("author_name") or []
    publishers = doc.get("publisher") or []
    return SearchHit(
        title=doc.get("title") or "Untitled",
        author=", ".join(authors[:2]) or None,
        year=doc.get("first_publish_year"),
        pages=doc.get("number_of_pages_median"),
        isbn=isbns[0] if isbns else None,
        publisher=publishers[0] if publishers else None,
        cover_url=f"{covers_base}/b/id/{cover_id}-M.jpg" if cover_id else None,
        openlibrary_key=doc.get("key"),
    )


def rank(
    docs: list[dict[str, Any]],
    *,
    title: str | None,
    author: str | None,
    covers_base: str,
) -> list[SearchHit]:
    hits = []
    for doc in docs:
        hit = to_hit(doc, covers_base=covers_base)
        hit.confidence = score(doc, title=title, author=author)
        hits.append(hit)
    hits.sort(key=lambda h: h.confidence, reverse=True)
    return hits


async def search(**kwargs: Any) -> list[SearchHit]:
    """Run a search and return hits, best first. Raises httpx errors upward."""
    settings = get_settings()
    title = kwargs.get("title")
    author = kwargs.get("author")

    # A bare phrase still gets fuzzy-scored against the title.
    if not title and kwargs.get("query"):
        title = kwargs["query"]

    params = build_params(**kwargs)
    async with httpx.AsyncClient(
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
    ) as client:
        response = await client.get(
            f"{settings.openlibrary_base}/search.json", params=params
        )
        response.raise_for_status()
        payload = response.json()

    return rank(
        payload.get("docs") or [],
        title=title,
        author=author,
        covers_base=settings.covers_base,
    )

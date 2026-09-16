"""Open Library client.

Open Library's search endpoint is free, needs no API key, and covers tens of
millions of editions. That single fact collapses the 'ship a book database'
problem into 'make one HTTP request'.

We ask for a narrow `fields` list so responses stay small, normalise each hit
into a BookCandidate, and score it against what the user actually typed so the
interface can lead with a best guess to confirm or reject.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

import httpx

from .config import get_settings
from .schemas import AdvancedSearchQuery, BookCandidate, SearchResults

FIELDS = ",".join(
    [
        "key",
        "title",
        "subtitle",
        "author_name",
        "first_publish_year",
        "publisher",
        "number_of_pages_median",
        "isbn",
        "language",
        "cover_i",
        "edition_count",
    ]
)

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_ARTICLES = {"the", "a", "an", "el", "la", "los", "las", "un", "una"}


def _normalise(text: str) -> str:
    text = _PUNCT.sub(" ", text.lower())
    words = [w for w in text.split() if w and w not in _ARTICLES]
    return " ".join(words)


def similarity(a: str, b: str) -> float:
    """0.0 - 1.0 similarity, ignoring case, punctuation and leading articles."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


def build_params(query: AdvancedSearchQuery) -> dict[str, str | int]:
    """Translate an advanced query into Open Library search parameters.

    Every filled field is sent as its own parameter, which Open Library ANDs
    together. Year ranges go into the free-text `q` as a range expression.
    """
    params: dict[str, str | int] = {"fields": FIELDS, "limit": query.limit}

    q_parts: list[str] = []
    if query.q:
        q_parts.append(query.q.strip())
    if query.year_from is not None or query.year_to is not None:
        lo = query.year_from if query.year_from is not None else "*"
        hi = query.year_to if query.year_to is not None else "*"
        q_parts.append(f"first_publish_year:[{lo} TO {hi}]")
    if q_parts:
        params["q"] = " ".join(q_parts)

    if query.title:
        params["title"] = query.title.strip()
    if query.author:
        params["author"] = query.author.strip()
    if query.subject:
        params["subject"] = query.subject.strip()
    if query.publisher:
        params["publisher"] = query.publisher.strip()
    if query.isbn:
        params["isbn"] = re.sub(r"[^0-9Xx]", "", query.isbn)
    if query.language:
        params["language"] = query.language.strip().lower()

    return params


def _pick_isbns(raw: list[str] | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    isbn10 = next((i for i in raw if len(i) == 10), None)
    isbn13 = next((i for i in raw if len(i) == 13), None)
    return isbn10, isbn13


def parse_doc(doc: dict) -> BookCandidate:
    """Turn one raw Open Library search document into a BookCandidate."""
    settings = get_settings()

    isbn10, isbn13 = _pick_isbns(doc.get("isbn"))
    cover_id = doc.get("cover_i")
    cover_url = (
        f"{settings.openlibrary_covers_url}/b/id/{cover_id}-M.jpg" if cover_id else None
    )

    authors = doc.get("author_name") or []
    publishers = doc.get("publisher") or []
    languages = doc.get("language") or []

    return BookCandidate(
        openlibrary_key=doc.get("key"),
        title=(doc.get("title") or "Untitled").strip(),
        subtitle=(doc.get("subtitle") or None),
        authors=", ".join(authors[:3]) if authors else None,
        publisher=publishers[0] if publishers else None,
        published_year=doc.get("first_publish_year"),
        page_count=doc.get("number_of_pages_median"),
        isbn10=isbn10,
        isbn13=isbn13,
        language=languages[0] if languages else None,
        cover_url=cover_url,
        edition_count=doc.get("edition_count") or 0,
    )


def score_candidate(candidate: BookCandidate, query: AdvancedSearchQuery) -> float:
    """How confident are we that this hit is the book the user meant?

    Title similarity carries most of the weight, author similarity the rest,
    with a small nudge for editions -- a book with many editions is more likely
    to be the well-known one somebody is thinking of.
    """
    wanted_title = query.title or query.q or ""
    title_score = similarity(wanted_title, candidate.title) if wanted_title else 0.5

    if query.author and candidate.authors:
        author_score = max(
            similarity(query.author, part.strip())
            for part in candidate.authors.split(",")
        )
    else:
        author_score = 0.0

    # If the user gave us an exact ISBN, trust it completely.
    if query.isbn:
        cleaned = re.sub(r"[^0-9Xx]", "", query.isbn).upper()
        if cleaned in {(candidate.isbn10 or "").upper(), (candidate.isbn13 or "")}:
            return 1.0

    weight_author = 0.35 if query.author else 0.0
    weight_title = 1.0 - weight_author - 0.05
    popularity = min(candidate.edition_count, 50) / 50 * 0.05

    return round(
        title_score * weight_title + author_score * weight_author + popularity, 4
    )


async def search(
    query: AdvancedSearchQuery, client: httpx.AsyncClient | None = None
) -> SearchResults:
    """Run a search and return scored, sorted candidates.

    Never raises on network trouble: a failed lookup returns `degraded=True`
    with an empty candidate list, so the interface can fall back to manual
    entry instead of showing an error page.
    """
    settings = get_settings()

    if query.is_empty():
        return SearchResults(
            query_echo=query, message="Type something to search for.", total_found=0
        )

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=settings.openlibrary_timeout,
            headers={"User-Agent": settings.openlibrary_user_agent},
        )

    try:
        response = await client.get(
            f"{settings.openlibrary_base_url}/search.json", params=build_params(query)
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return SearchResults(
            query_echo=query,
            degraded=True,
            message=(
                "Could not reach Open Library. You can still add this book by hand."
            ),
        )
    finally:
        if owns_client:
            await client.aclose()

    docs = payload.get("docs") or []
    candidates = []
    for doc in docs:
        candidate = parse_doc(doc)
        candidate.match_score = score_candidate(candidate, query)
        candidates.append(candidate)

    candidates.sort(key=lambda c: c.match_score, reverse=True)

    best = candidates[0] if candidates else None
    message = None
    if not candidates:
        message = "Nothing matched. Try fewer fields, or add it by hand."
    elif best is not None and best.match_score < 0.55:
        message = "Nothing looks like a close match -- check before you confirm."

    return SearchResults(
        query_echo=query,
        best_match=best,
        candidates=candidates,
        total_found=payload.get("numFound") or payload.get("num_found") or len(docs),
        message=message,
    )

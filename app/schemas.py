"""Pydantic models for request bodies and API responses."""

from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalise_hex(value: str) -> str:
    value = value.strip()
    if not HEX_RE.match(value):
        raise ValueError("Colour must be a hex value like #b96bff.")
    value = value.lower()
    if len(value) == 4:  # expand #abc -> #aabbcc
        value = "#" + "".join(ch * 2 for ch in value[1:])
    return value


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class SessionInfo(BaseModel):
    authenticated: bool
    username: str | None = None


# --------------------------------------------------------------------------
# Tags & categories
# --------------------------------------------------------------------------


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = "#b96bff"
    icon: str | None = Field(default=None, max_length=16)
    role: str | None = Field(default=None, max_length=16)
    position: int = 0

    @field_validator("color")
    @classmethod
    def _color(cls, v: str) -> str:
        return normalise_hex(v)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()


class TagCreate(TagBase):
    category_id: int


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = None
    icon: str | None = Field(default=None, max_length=16)
    role: str | None = Field(default=None, max_length=16)
    position: int | None = None
    category_id: int | None = None

    @field_validator("color")
    @classmethod
    def _color(cls, v: str | None) -> str | None:
        return None if v is None else normalise_hex(v)


class TagOut(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    is_preset: bool
    book_count: int = 0


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    position: int = 0
    exclusive: bool = False


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    position: int | None = None
    exclusive: bool | None = None


class CategoryOut(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_preset: bool
    tags: list[TagOut] = []


# --------------------------------------------------------------------------
# Books
# --------------------------------------------------------------------------


class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    subtitle: str | None = Field(default=None, max_length=500)
    authors: str | None = Field(default=None, max_length=500)
    series: str | None = Field(default=None, max_length=255)
    publisher: str | None = Field(default=None, max_length=255)
    published_year: int | None = Field(default=None, ge=-3000, le=2200)
    page_count: int | None = Field(default=None, ge=0, le=100_000)
    isbn10: str | None = Field(default=None, max_length=13)
    isbn13: str | None = Field(default=None, max_length=17)
    language: str | None = Field(default=None, max_length=32)
    cover_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    notes: str | None = None
    current_page: int = Field(default=0, ge=0)
    date_started: date | None = None
    date_finished: date | None = None

    @field_validator("rating")
    @classmethod
    def _half_steps(cls, v: float | None) -> float | None:
        if v is None:
            return None
        if round(v * 2) != v * 2:
            raise ValueError("Rating must land on a half star (0.5, 1.0, 1.5 ...).")
        return float(v)

    @field_validator("title", "authors")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class BookCreate(BookBase):
    openlibrary_key: str | None = None
    source: str = "manual"
    tag_ids: list[int] = []


class BookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=500)
    subtitle: str | None = None
    authors: str | None = None
    series: str | None = None
    publisher: str | None = None
    published_year: int | None = None
    page_count: int | None = None
    isbn10: str | None = None
    isbn13: str | None = None
    language: str | None = None
    cover_url: str | None = None
    description: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    notes: str | None = None
    current_page: int | None = Field(default=None, ge=0)
    date_started: date | None = None
    date_finished: date | None = None
    tag_ids: list[int] | None = None

    @field_validator("rating")
    @classmethod
    def _half_steps(cls, v: float | None) -> float | None:
        if v is not None and round(v * 2) != v * 2:
            raise ValueError("Rating must land on a half star (0.5, 1.0, 1.5 ...).")
        return v


class BookOut(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    openlibrary_key: str | None = None
    source: str
    progress_percent: float
    created_at: datetime
    updated_at: datetime
    tags: list[TagOut] = []


class BookPage(BaseModel):
    items: list[BookOut]
    total: int
    limit: int
    offset: int


# --------------------------------------------------------------------------
# Open Library search
# --------------------------------------------------------------------------


class AdvancedSearchQuery(BaseModel):
    """Every field is optional; the ones that are filled in are ANDed together."""

    q: str | None = None
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    publisher: str | None = None
    isbn: str | None = None
    year_from: int | None = Field(default=None, ge=-3000, le=2200)
    year_to: int | None = Field(default=None, ge=-3000, le=2200)
    language: str | None = Field(default=None, max_length=8)
    limit: int = Field(default=20, ge=1, le=50)

    def is_empty(self) -> bool:
        return not any(
            [
                self.q,
                self.title,
                self.author,
                self.subject,
                self.publisher,
                self.isbn,
                self.year_from,
                self.year_to,
            ]
        )


class BookCandidate(BaseModel):
    """A normalised Open Library hit, ready to be turned into a Book."""

    openlibrary_key: str | None = None
    title: str
    subtitle: str | None = None
    authors: str | None = None
    publisher: str | None = None
    published_year: int | None = None
    page_count: int | None = None
    isbn10: str | None = None
    isbn13: str | None = None
    language: str | None = None
    cover_url: str | None = None
    edition_count: int = 0
    match_score: float = 0.0


class SearchResults(BaseModel):
    query_echo: AdvancedSearchQuery
    best_match: BookCandidate | None = None
    candidates: list[BookCandidate] = []
    total_found: int = 0
    degraded: bool = False
    message: str | None = None


# --------------------------------------------------------------------------
# Stats & goals
# --------------------------------------------------------------------------


class GoalIn(BaseModel):
    year: int = Field(ge=1900, le=2200)
    target_books: int = Field(default=0, ge=0, le=10_000)
    target_pages: int = Field(default=0, ge=0, le=10_000_000)


class GoalOut(GoalIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    books_finished: int = 0
    pages_read: int = 0
    books_percent: float = 0.0
    pages_percent: float = 0.0


class TagSlice(BaseModel):
    tag_id: int
    name: str
    color: str
    count: int


class MonthlyCount(BaseModel):
    month: int
    count: int
    pages: int


class StatsOut(BaseModel):
    total_books: int
    finished_all_time: int
    currently_reading: int
    pages_all_time: int
    average_rating: float | None
    rated_count: int
    longest_book: str | None
    year: int
    finished_this_year: int
    pages_this_year: int
    monthly: list[MonthlyCount]
    by_tag: list[TagSlice]
    goal: GoalOut | None


# --------------------------------------------------------------------------
# Preferences
# --------------------------------------------------------------------------


class PreferenceIn(BaseModel):
    value: str = Field(max_length=2000)


class ImportReport(BaseModel):
    created: int
    skipped: int
    errors: list[str] = []

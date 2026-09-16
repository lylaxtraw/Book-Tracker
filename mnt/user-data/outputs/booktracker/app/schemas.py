"""Request and response shapes."""

from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _check_hex(value: str) -> str:
    value = value.strip()
    if not HEX.match(value):
        raise ValueError("Color must be a hex value like #A472F0")
    return value.upper()


# --------------------------------------------------------------------------- tags


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    exclusive: bool = False
    position: int = 0


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    exclusive: bool | None = None
    position: int | None = None


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str = "#A472F0"
    category_id: int
    position: int = 0

    _hex = field_validator("color")(_check_hex)


class TagPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = None
    category_id: int | None = None
    position: int | None = None

    @field_validator("color")
    @classmethod
    def _hex(cls, v: str | None) -> str | None:
        return None if v is None else _check_hex(v)


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
    category_id: int
    is_preset: bool
    position: int


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    exclusive: bool
    is_preset: bool
    position: int
    tags: list[TagOut] = []


# -------------------------------------------------------------------------- books


class BookIn(BaseModel):
    title: str = Field(min_length=1, max_length=400)
    author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    year: int | None = None
    pages: int | None = Field(default=None, ge=0)
    cover_url: str | None = None
    openlibrary_key: str | None = None
    description: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    notes: str | None = None
    progress_pages: int = Field(default=0, ge=0)
    started_on: date | None = None
    finished_on: date | None = None
    tag_ids: list[int] = []


class BookPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=400)
    author: str | None = None
    isbn: str | None = None
    publisher: str | None = None
    year: int | None = None
    pages: int | None = Field(default=None, ge=0)
    cover_url: str | None = None
    description: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    notes: str | None = None
    progress_pages: int | None = Field(default=None, ge=0)
    started_on: date | None = None
    finished_on: date | None = None
    tag_ids: list[int] | None = None


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str | None
    isbn: str | None
    publisher: str | None
    year: int | None
    pages: int | None
    cover_url: str | None
    openlibrary_key: str | None
    description: str | None
    rating: float | None
    notes: str | None
    progress_pages: int
    progress_percent: int
    started_on: date | None
    finished_on: date | None
    added_at: datetime
    tags: list[TagOut] = []


# ------------------------------------------------------------------------ search


class SearchHit(BaseModel):
    title: str
    author: str | None = None
    year: int | None = None
    pages: int | None = None
    isbn: str | None = None
    publisher: str | None = None
    cover_url: str | None = None
    openlibrary_key: str | None = None
    confidence: int = 0


# ------------------------------------------------------------------- stats & auth


class GoalIn(BaseModel):
    year: int
    target_books: int = Field(ge=0, le=10_000)


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year: int
    target_books: int


class YearCount(BaseModel):
    year: int
    books: int
    pages: int


class TagCount(BaseModel):
    tag: TagOut
    books: int


class Stats(BaseModel):
    total_books: int
    finished_books: int
    reading_now: int
    pages_read: int
    average_rating: float | None
    per_year: list[YearCount]
    per_tag: list[TagCount]
    goal: GoalOut | None
    goal_completed: int


class LoginIn(BaseModel):
    password: str

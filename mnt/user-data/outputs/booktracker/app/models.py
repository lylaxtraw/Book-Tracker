"""ORM models.

Shape of the data:

    Category ──< Tag ──< BookTag >── Book

A Category groups tags ("Status", "Shelf", anything Koy invents). If a category is
marked `exclusive`, a book can only carry one tag from it — that is what makes
"Reading" replace "Want to read" automatically instead of stacking up.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


book_tags = Table(
    "book_tags",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    tags: Mapped[list[Tag]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="Tag.position",
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", name="uq_tag_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    color: Mapped[str] = mapped_column(String(9), default="#A472F0")
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[Category] = relationship(back_populates="tags")
    books: Mapped[list[Book]] = relationship(
        secondary=book_tags, back_populates="tags"
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(400))
    author: Mapped[str | None] = mapped_column(String(300), default=None)
    isbn: Mapped[str | None] = mapped_column(String(20), default=None)
    publisher: Mapped[str | None] = mapped_column(String(200), default=None)
    year: Mapped[int | None] = mapped_column(Integer, default=None)
    pages: Mapped[int | None] = mapped_column(Integer, default=None)
    cover_url: Mapped[str | None] = mapped_column(String(500), default=None)
    openlibrary_key: Mapped[str | None] = mapped_column(String(80), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Personal layer
    rating: Mapped[float | None] = mapped_column(Float, default=None)  # 0.5 – 5.0
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    progress_pages: Mapped[int] = mapped_column(Integer, default=0)
    started_on: Mapped[date | None] = mapped_column(Date, default=None)
    finished_on: Mapped[date | None] = mapped_column(Date, default=None)

    added_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    tags: Mapped[list[Tag]] = relationship(
        secondary=book_tags, back_populates="books", lazy="selectin"
    )

    @property
    def progress_percent(self) -> int:
        """Whole-number percentage, clamped. Finished books always read 100."""
        if self.finished_on:
            return 100
        if not self.pages or self.pages <= 0:
            return 0
        return max(0, min(100, round(self.progress_pages / self.pages * 100)))


class Goal(Base):
    """One reading target per year."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, unique=True)
    target_books: Mapped[int] = mapped_column(Integer, default=12)

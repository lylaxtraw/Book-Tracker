"""ORM models.

The shape of the data is deliberately small: a Book, a Tag, and the Category a
Tag lives in. Everything a user can see in the interface is a row they are
allowed to rename, recolour, reorder or delete -- including the seven presets.
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


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


book_tags = Table(
    "book_tags",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """A single-row table. This instance belongs to one reader."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TagCategory(Base):
    """A heading that tags group themselves under, e.g. 'Status' or 'Genre'."""

    __tablename__ = "tag_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Exclusive categories allow at most one tag per book (a book is either
    # 'Reading' or 'Read', never both). Non-exclusive ones allow many.
    exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    tags: Mapped[list["Tag"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="Tag.position",
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", name="uq_tag_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # Hex colour, always stored as '#rrggbb' lowercase.
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(16))
    # A stable machine name that behaviour keys on, so renaming 'Read' to
    # 'Finished' (or to Spanish) does not break the statistics or the
    # automatic start/finish dates. One of: reading, finished, wishlist,
    # owned, dnf, lent -- or NULL for an ordinary tag.
    role: Mapped[str | None] = mapped_column(String(16), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("tag_categories.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[TagCategory] = relationship(back_populates="tags")

    books: Mapped[list["Book"]] = relationship(
        secondary=book_tags, back_populates="tags"
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- Bibliographic data ---
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(500))
    authors: Mapped[str | None] = mapped_column(String(500))  # comma separated
    series: Mapped[str | None] = mapped_column(String(255))
    publisher: Mapped[str | None] = mapped_column(String(255))
    published_year: Mapped[int | None] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)
    isbn10: Mapped[str | None] = mapped_column(String(13))
    isbn13: Mapped[str | None] = mapped_column(String(17))
    language: Mapped[str | None] = mapped_column(String(32))
    cover_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)

    # --- Provenance ---
    openlibrary_key: Mapped[str | None] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")

    # --- Personal data ---
    rating: Mapped[float | None] = mapped_column(Float)  # 0.5 .. 5.0, half steps
    notes: Mapped[str | None] = mapped_column(Text)
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    date_started: Mapped[date | None] = mapped_column(Date)
    date_finished: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    tags: Mapped[list[Tag]] = relationship(
        secondary=book_tags, back_populates="books", lazy="selectin"
    )

    @property
    def progress_percent(self) -> float:
        """How far through the book the reader is, 0-100."""
        if not self.page_count or self.page_count <= 0:
            return 100.0 if self.date_finished else 0.0
        if self.date_finished:
            return 100.0
        pct = (self.current_page or 0) / self.page_count * 100
        return round(min(max(pct, 0.0), 100.0), 1)


class ReadingGoal(Base):
    __tablename__ = "reading_goals"
    __table_args__ = (UniqueConstraint("year", name="uq_goal_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_books: Mapped[int] = mapped_column(Integer, default=0)
    target_pages: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Preference(Base):
    """Free-form key/value store for interface preferences (theme, etc.)."""

    __tablename__ = "preferences"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")

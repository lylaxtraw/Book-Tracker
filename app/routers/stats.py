"""Reading statistics and the yearly goal."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Book, ReadingGoal, Tag, book_tags
from ..schemas import GoalIn, GoalOut, MonthlyCount, StatsOut, TagSlice

router = APIRouter(
    prefix="/api", tags=["stats"], dependencies=[Depends(current_user)]
)


def _finished_in_year(db: Session, year: int) -> list[Book]:
    return (
        db.query(Book)
        .filter(
            Book.date_finished >= date(year, 1, 1),
            Book.date_finished <= date(year, 12, 31),
        )
        .all()
    )


def _goal_out(db: Session, year: int) -> GoalOut | None:
    goal = db.query(ReadingGoal).filter(ReadingGoal.year == year).one_or_none()
    if goal is None:
        return None

    finished = _finished_in_year(db, year)
    pages = sum(b.page_count or 0 for b in finished)

    return GoalOut(
        id=goal.id,
        year=goal.year,
        target_books=goal.target_books,
        target_pages=goal.target_pages,
        books_finished=len(finished),
        pages_read=pages,
        books_percent=(
            round(len(finished) / goal.target_books * 100, 1)
            if goal.target_books
            else 0.0
        ),
        pages_percent=(
            round(pages / goal.target_pages * 100, 1) if goal.target_pages else 0.0
        ),
    )


@router.get("/stats", response_model=StatsOut)
def read_stats(
    db: Session = Depends(get_db), year: int | None = Query(default=None)
) -> StatsOut:
    year = year or date.today().year

    total_books = db.query(func.count(Book.id)).scalar() or 0
    finished_all = (
        db.query(func.count(Book.id)).filter(Book.date_finished.is_not(None)).scalar()
        or 0
    )
    pages_all = (
        db.query(func.coalesce(func.sum(Book.page_count), 0))
        .filter(Book.date_finished.is_not(None))
        .scalar()
        or 0
    )

    reading_now = (
        db.query(func.count(func.distinct(Book.id)))
        .join(book_tags, book_tags.c.book_id == Book.id)
        .join(Tag, Tag.id == book_tags.c.tag_id)
        .filter(Tag.role == "reading")
        .scalar()
        or 0
    )

    rated = db.query(Book.rating).filter(Book.rating.is_not(None)).all()
    ratings = [r[0] for r in rated]
    average_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    longest = (
        db.query(Book.title)
        .filter(Book.page_count.is_not(None))
        .order_by(Book.page_count.desc())
        .limit(1)
        .scalar()
    )

    finished_this_year = _finished_in_year(db, year)
    pages_this_year = sum(b.page_count or 0 for b in finished_this_year)

    buckets: dict[int, list[int]] = {m: [0, 0] for m in range(1, 13)}
    for book in finished_this_year:
        if book.date_finished is None:
            continue
        slot = buckets[book.date_finished.month]
        slot[0] += 1
        slot[1] += book.page_count or 0

    monthly = [
        MonthlyCount(month=m, count=v[0], pages=v[1]) for m, v in sorted(buckets.items())
    ]

    tag_rows = db.execute(
        select(Tag.id, Tag.name, Tag.color, func.count(book_tags.c.book_id))
        .join(book_tags, book_tags.c.tag_id == Tag.id, isouter=True)
        .group_by(Tag.id)
        .order_by(func.count(book_tags.c.book_id).desc())
    ).all()

    by_tag = [
        TagSlice(tag_id=tid, name=name, color=color, count=count)
        for tid, name, color, count in tag_rows
    ]

    return StatsOut(
        total_books=total_books,
        finished_all_time=finished_all,
        currently_reading=reading_now,
        pages_all_time=int(pages_all),
        average_rating=average_rating,
        rated_count=len(ratings),
        longest_book=longest,
        year=year,
        finished_this_year=len(finished_this_year),
        pages_this_year=pages_this_year,
        monthly=monthly,
        by_tag=by_tag,
        goal=_goal_out(db, year),
    )


@router.get("/goals/{year}", response_model=GoalOut | None)
def read_goal(year: int, db: Session = Depends(get_db)) -> GoalOut | None:
    return _goal_out(db, year)


@router.put("/goals", response_model=GoalOut)
def set_goal(payload: GoalIn, db: Session = Depends(get_db)) -> GoalOut:
    goal = db.query(ReadingGoal).filter(ReadingGoal.year == payload.year).one_or_none()
    if goal is None:
        goal = ReadingGoal(year=payload.year)
        db.add(goal)
    goal.target_books = payload.target_books
    goal.target_pages = payload.target_pages
    db.commit()
    result = _goal_out(db, payload.year)
    assert result is not None
    return result

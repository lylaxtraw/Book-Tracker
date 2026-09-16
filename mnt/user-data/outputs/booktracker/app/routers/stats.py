from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import Book, Goal, Tag
from ..schemas import GoalIn, GoalOut, Stats, TagCount, TagOut, YearCount

router = APIRouter(prefix="/api", tags=["stats"], dependencies=[Depends(require_auth)])

READING_TAG = "Reading"


@router.get("/stats", response_model=Stats)
def read_stats(db: Session = Depends(get_db), year: int | None = None):
    target_year = year or date.today().year
    books = db.query(Book).all()

    finished = [b for b in books if b.finished_on is not None]

    per_year_books: dict[int, int] = defaultdict(int)
    per_year_pages: dict[int, int] = defaultdict(int)
    for book in finished:
        per_year_books[book.finished_on.year] += 1
        per_year_pages[book.finished_on.year] += book.pages or 0

    per_year = [
        YearCount(year=y, books=per_year_books[y], pages=per_year_pages[y])
        for y in sorted(per_year_books, reverse=True)
    ]

    # Pages read = every finished book in full, plus progress on the rest.
    pages_read = sum(b.pages or 0 for b in finished) + sum(
        b.progress_pages for b in books if b.finished_on is None
    )

    rated = [b.rating for b in books if b.rating]
    average = round(sum(rated) / len(rated), 2) if rated else None

    reading_now = sum(
        1 for b in books if any(t.name == READING_TAG for t in b.tags)
    )

    per_tag = []
    for tag in db.query(Tag).order_by(Tag.category_id, Tag.position, Tag.id).all():
        per_tag.append(TagCount(tag=TagOut.model_validate(tag), books=len(tag.books)))

    goal = db.query(Goal).filter_by(year=target_year).one_or_none()

    return Stats(
        total_books=len(books),
        finished_books=len(finished),
        reading_now=reading_now,
        pages_read=pages_read,
        average_rating=average,
        per_year=per_year,
        per_tag=per_tag,
        goal=GoalOut.model_validate(goal) if goal else None,
        goal_completed=per_year_books.get(target_year, 0),
    )


@router.get("/goals", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db)):
    return db.query(Goal).order_by(Goal.year.desc()).all()


@router.put("/goals", response_model=GoalOut)
def set_goal(payload: GoalIn, db: Session = Depends(get_db)):
    goal = db.query(Goal).filter_by(year=payload.year).one_or_none()
    if goal is None:
        goal = Goal(year=payload.year, target_books=payload.target_books)
        db.add(goal)
    else:
        goal.target_books = payload.target_books
    db.commit()
    db.refresh(goal)
    return goal

"""Tags and the categories they sort themselves into.

Presets are not special-cased anywhere except the delete warning: they are rows
like any other, so renaming 'Want to Read' to 'Someday' or recolouring it is a
single PATCH.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Tag, TagCategory, User, book_tags
from ..schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    TagCreate,
    TagOut,
    TagUpdate,
)

router = APIRouter(
    prefix="/api", tags=["tags"], dependencies=[Depends(current_user)]
)


def _book_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(book_tags.c.tag_id, func.count(book_tags.c.book_id)).group_by(
            book_tags.c.tag_id
        )
    ).all()
    return {tag_id: count for tag_id, count in rows}


def _tag_out(tag: Tag, counts: dict[int, int]) -> TagOut:
    return TagOut(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        icon=tag.icon,
        role=tag.role,
        position=tag.position,
        category_id=tag.category_id,
        is_preset=tag.is_preset,
        book_count=counts.get(tag.id, 0),
    )


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryOut]:
    counts = _book_counts(db)
    categories = (
        db.query(TagCategory)
        .order_by(TagCategory.position, TagCategory.name)
        .all()
    )
    return [
        CategoryOut(
            id=c.id,
            name=c.name,
            description=c.description,
            position=c.position,
            exclusive=c.exclusive,
            is_preset=c.is_preset,
            tags=[_tag_out(t, counts) for t in sorted(c.tags, key=lambda t: t.position)],
        )
        for c in categories
    ]


@router.post(
    "/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED
)
def create_category(
    payload: CategoryCreate, db: Session = Depends(get_db)
) -> CategoryOut:
    name = payload.name.strip()
    if db.query(TagCategory).filter(func.lower(TagCategory.name) == name.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A category called '{name}' already exists.",
        )
    category = TagCategory(
        name=name,
        description=payload.description,
        position=payload.position,
        exclusive=payload.exclusive,
        is_preset=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryOut(
        id=category.id,
        name=category.name,
        description=category.description,
        position=category.position,
        exclusive=category.exclusive,
        is_preset=category.is_preset,
        tags=[],
    )


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
) -> CategoryOut:
    category = db.get(TagCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        new_name = data["name"].strip()
        clash = (
            db.query(TagCategory)
            .filter(
                func.lower(TagCategory.name) == new_name.lower(),
                TagCategory.id != category_id,
            )
            .first()
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A category called '{new_name}' already exists.",
            )
        category.name = new_name
        data.pop("name")

    for field, value in data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    counts = _book_counts(db)
    return CategoryOut(
        id=category.id,
        name=category.name,
        description=category.description,
        position=category.position,
        exclusive=category.exclusive,
        is_preset=category.is_preset,
        tags=[_tag_out(t, counts) for t in sorted(category.tags, key=lambda t: t.position)],
    )


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    category = db.get(TagCategory, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    db.delete(category)  # cascades to its tags, which cascades to book_tags rows
    db.commit()


# --------------------------------------------------------------------------
# Tags
# --------------------------------------------------------------------------


@router.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)) -> list[TagOut]:
    counts = _book_counts(db)
    tags = db.query(Tag).order_by(Tag.category_id, Tag.position, Tag.name).all()
    return [_tag_out(t, counts) for t in tags]


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)) -> TagOut:
    if db.get(TagCategory, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    name = payload.name.strip()
    if db.query(Tag).filter(func.lower(Tag.name) == name.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tag called '{name}' already exists.",
        )
    tag = Tag(
        name=name,
        color=payload.color,
        icon=payload.icon,
        role=payload.role,
        position=payload.position,
        category_id=payload.category_id,
        is_preset=False,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _tag_out(tag, {})


@router.patch("/tags/{tag_id}", response_model=TagOut)
def update_tag(
    tag_id: int, payload: TagUpdate, db: Session = Depends(get_db)
) -> TagOut:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found.")

    data = payload.model_dump(exclude_unset=True)

    if "category_id" in data and data["category_id"] is not None:
        if db.get(TagCategory, data["category_id"]) is None:
            raise HTTPException(status_code=404, detail="Category not found.")

    if "name" in data and data["name"]:
        new_name = data["name"].strip()
        clash = (
            db.query(Tag)
            .filter(func.lower(Tag.name) == new_name.lower(), Tag.id != tag_id)
            .first()
        )
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A tag called '{new_name}' already exists.",
            )
        data["name"] = new_name

    for field, value in data.items():
        setattr(tag, field, value)

    db.commit()
    db.refresh(tag)
    return _tag_out(tag, _book_counts(db))


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_tag(tag_id: int, db: Session = Depends(get_db)) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found.")
    db.delete(tag)
    db.commit()


@router.post("/tags/reorder", response_model=list[TagOut])
def reorder_tags(
    order: list[int], db: Session = Depends(get_db), _: User = Depends(current_user)
) -> list[TagOut]:
    """Accept a list of tag ids and store that sequence as their positions."""
    tags = {t.id: t for t in db.query(Tag).filter(Tag.id.in_(order)).all()}
    missing = [i for i in order if i not in tags]
    if missing:
        raise HTTPException(status_code=404, detail=f"Unknown tag ids: {missing}")
    for position, tag_id in enumerate(order):
        tags[tag_id].position = position
    db.commit()
    counts = _book_counts(db)
    return [_tag_out(tags[i], counts) for i in order]

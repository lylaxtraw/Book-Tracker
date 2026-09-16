from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..database import get_db
from ..models import Category, Tag
from ..schemas import CategoryIn, CategoryOut, CategoryPatch, TagIn, TagOut, TagPatch

router = APIRouter(prefix="/api", tags=["tags"], dependencies=[Depends(require_auth)])


def _get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No category with that id")
    return category


def _get_tag(db: Session, tag_id: int) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No tag with that id")
    return tag


# ------------------------------------------------------------------ categories


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.position, Category.id).all()


@router.post(
    "/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED
)
def create_category(payload: CategoryIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if db.query(Category).filter_by(name=name).one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A category called “{name}” already exists"
        )
    category = Category(
        name=name, exclusive=payload.exclusive, position=payload.position
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, payload: CategoryPatch, db: Session = Depends(get_db)
):
    category = _get_category(db, category_id)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data:
        name = data["name"].strip()
        clash = db.query(Category).filter(Category.name == name).one_or_none()
        if clash and clash.id != category.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"A category called “{name}” already exists"
            )
        category.name = name

    for field in ("exclusive", "position"):
        if field in data:
            setattr(category, field, data[field])

    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = _get_category(db, category_id)
    if category.is_preset:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Built-in categories can be renamed but not deleted",
        )
    db.delete(category)
    db.commit()


# ------------------------------------------------------------------------ tags


@router.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.query(Tag).order_by(Tag.category_id, Tag.position, Tag.id).all()


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    _get_category(db, payload.category_id)
    if db.query(Tag).filter_by(name=name).one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"A tag called “{name}” already exists"
        )
    tag = Tag(
        name=name,
        color=payload.color,
        category_id=payload.category_id,
        position=payload.position,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.patch("/tags/{tag_id}", response_model=TagOut)
def update_tag(tag_id: int, payload: TagPatch, db: Session = Depends(get_db)):
    tag = _get_tag(db, tag_id)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data:
        name = data["name"].strip()
        clash = db.query(Tag).filter(Tag.name == name).one_or_none()
        if clash and clash.id != tag.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"A tag called “{name}” already exists"
            )
        tag.name = name

    if "category_id" in data and data["category_id"] is not None:
        _get_category(db, data["category_id"])
        tag.category_id = data["category_id"]

    for field in ("color", "position"):
        if data.get(field) is not None:
            setattr(tag, field, data[field])

    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = _get_tag(db, tag_id)
    db.delete(tag)
    db.commit()

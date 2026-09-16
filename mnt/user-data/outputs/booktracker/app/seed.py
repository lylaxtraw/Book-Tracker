"""The tags the library starts with.

Seven presets, one per colour of the rainbow, filed into two categories.
"Status" is exclusive — a book is either being read or finished, never both —
while "Shelf" is not, because a book can be owned *and* lent out.

Everything here is editable from the Tags screen. These are a starting point,
not a cage.
"""

from sqlalchemy.orm import Session

from .models import Category, Tag

RAINBOW = {
    "red": "#E5484D",
    "orange": "#F2801F",
    "yellow": "#FFC65C",
    "green": "#3DBE7C",
    "blue": "#4A8FE7",
    "indigo": "#6C7BE8",
    "violet": "#A472F0",
}

PRESET_CATEGORIES = [
    # (name, exclusive, position, [(tag name, rainbow colour, position)])
    (
        "Status",
        True,
        0,
        [
            ("Want to read", "blue", 0),
            ("Reading", "yellow", 1),
            ("Read", "green", 2),
            ("Gave up", "red", 3),
        ],
    ),
    (
        "Shelf",
        False,
        1,
        [
            ("Owned", "violet", 0),
            ("Wishlist", "indigo", 1),
            ("Borrowed", "orange", 2),
        ],
    ),
]

# New tags Koy makes without picking a category land here.
CUSTOM_CATEGORY = "My tags"


def seed_presets(db: Session) -> None:
    """Idempotent: safe to call on every startup."""
    for name, exclusive, position, tags in PRESET_CATEGORIES:
        category = db.query(Category).filter_by(name=name).one_or_none()
        if category is None:
            category = Category(
                name=name, exclusive=exclusive, is_preset=True, position=position
            )
            db.add(category)
            db.flush()

        for tag_name, colour, tag_position in tags:
            exists = db.query(Tag).filter_by(name=tag_name).one_or_none()
            if exists is None:
                db.add(
                    Tag(
                        name=tag_name,
                        color=RAINBOW[colour],
                        category_id=category.id,
                        is_preset=True,
                        position=tag_position,
                    )
                )

    if db.query(Category).filter_by(name=CUSTOM_CATEGORY).one_or_none() is None:
        db.add(Category(name=CUSTOM_CATEGORY, exclusive=False, position=2))

    db.commit()


def custom_category_id(db: Session) -> int:
    category = db.query(Category).filter_by(name=CUSTOM_CATEGORY).one_or_none()
    if category is None:
        category = Category(name=CUSTOM_CATEGORY, exclusive=False, position=2)
        db.add(category)
        db.commit()
        db.refresh(category)
    return category.id

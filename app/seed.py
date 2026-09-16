"""First-boot seed data.

Seven preset tags, one per colour of the rainbow. They live in an exclusive
'Status' category, which is what makes a book sort itself onto exactly one
shelf. Everything here is editable afterwards -- the presets are ordinary rows
with `is_preset=True`, which only affects the warning shown before deleting one.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .auth import hash_password
from .config import get_settings
from .models import Preference, Tag, TagCategory, User

# The seven, in spectrum order.
RAINBOW = {
    "red": "#ff5c6b",
    "orange": "#ff9f45",
    "yellow": "#ffd93d",
    "green": "#5cd68a",
    "blue": "#4ea8ff",
    "indigo": "#7b7bff",
    "violet": "#b96bff",
}

PRESET_CATEGORIES: list[dict] = [
    {
        # Exclusive: a book is in exactly one of these at a time, which is what
        # makes it sort itself onto a single shelf.
        "name": "Status",
        "description": "Where a book sits in your reading right now.",
        "position": 0,
        "exclusive": True,
        "tags": [
            {"name": "Did Not Finish", "color": RAINBOW["red"], "icon": "\u2716", "role": "dnf"},
            {"name": "Reading", "color": RAINBOW["orange"], "icon": "\u25d0", "role": "reading"},
            {"name": "Want to Read", "color": RAINBOW["yellow"], "icon": "\u2727", "role": "wishlist"},
            {"name": "Read", "color": RAINBOW["blue"], "icon": "\u2713", "role": "finished"},
        ],
    },
    {
        # Not exclusive: a book can be owned, lent out and beloved all at once.
        "name": "Shelf",
        "description": "Where the physical copy is, and how you feel about it.",
        "position": 1,
        "exclusive": False,
        "tags": [
            {"name": "Owned", "color": RAINBOW["green"], "icon": "\u25c6", "role": "owned"},
            {"name": "Lent Out", "color": RAINBOW["indigo"], "icon": "\u2192", "role": "lent"},
            {"name": "Favourite", "color": RAINBOW["violet"], "icon": "\u2605", "role": "favourite"},
        ],
    },
    {
        "name": "Genre",
        "description": "Add your own. Nothing here is fixed.",
        "position": 2,
        "exclusive": False,
        "tags": [],
    },
    {
        "name": "Mood",
        "description": "How a book felt, not what it was about.",
        "position": 3,
        "exclusive": False,
        "tags": [],
    },
]

DEFAULT_PREFERENCES = {
    "theme.accent": "#8a6fe8",
    "theme.ember": "#f5c842",
    "splash.enabled": "true",
    "library.default_view": "grid",
    "library.default_sort": "recent",
}


def seed_tags(db: Session) -> None:
    """Insert preset categories and tags if, and only if, none exist yet."""
    if db.query(TagCategory).count() > 0:
        return

    for cat_spec in PRESET_CATEGORIES:
        category = TagCategory(
            name=cat_spec["name"],
            description=cat_spec["description"],
            position=cat_spec["position"],
            exclusive=cat_spec["exclusive"],
            is_preset=True,
        )
        db.add(category)
        db.flush()
        for position, tag_spec in enumerate(cat_spec["tags"]):
            db.add(
                Tag(
                    name=tag_spec["name"],
                    color=tag_spec["color"],
                    icon=tag_spec["icon"],
                    role=tag_spec.get("role"),
                    position=position,
                    is_preset=True,
                    category_id=category.id,
                )
            )
    db.commit()


def seed_preferences(db: Session) -> None:
    existing = {p.key for p in db.query(Preference).all()}
    for key, value in DEFAULT_PREFERENCES.items():
        if key not in existing:
            db.add(Preference(key=key, value=value))
    db.commit()


def seed_owner(db: Session) -> None:
    """Create the single account from environment settings, once."""
    if db.query(User).count() > 0:
        return
    settings = get_settings()
    db.add(
        User(
            username=settings.owner_username.strip().lower(),
            password_hash=hash_password(settings.owner_password),
        )
    )
    db.commit()


def seed_all(db: Session) -> None:
    seed_owner(db)
    seed_tags(db)
    seed_preferences(db)

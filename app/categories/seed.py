"""The starter category tree, loaded once into an empty database.

`starter.json` was generated from `docs/Categories.xlsx` with the four changes
recorded in plan 03 (R1-R4); see `docs/plans/03-categories.md` for what changed
and why.

The file is validated as a whole and written in one transaction, so a bad file
leaves the database as it was instead of half a tree.
"""

import json
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.categories.errors import CategoryError
from app.categories.service import NAME_MAX_LENGTH
from app.models import Category, CategoryGroup

STARTER_FILE = Path(__file__).with_name("starter.json")


class StarterGroup(BaseModel):
    name: str
    is_income: bool = False
    categories: list[str]


def load_starter_tree(path: Path = STARTER_FILE) -> list[StarterGroup]:
    tree = [StarterGroup(**group) for group in json.loads(path.read_text())]
    check_tree(tree)
    return tree


def apply_starter_tree(
    db: Session,
    tree: list[StarterGroup] | None = None,
    *,
    replace: bool = False,
) -> tuple[int, int]:
    """Create the starter groups and categories, in one commit.

    Returns how many of each were created. Refuses a database that already has
    groups unless `replace` is set, which clears the tree first.
    """
    groups = load_starter_tree() if tree is None else tree
    check_tree(groups)

    if replace:
        _clear(db)
    elif db.scalar(select(CategoryGroup.id)) is not None:
        raise CategoryError(
            "This database already has category groups. "
            "Use --replace to delete them and load the starter tree."
        )

    for group_position, starter in enumerate(groups):
        group = CategoryGroup(
            name=starter.name,
            is_income=starter.is_income,
            sort_order=group_position,
        )
        db.add(group)
        # Flush only to get group.id; everything still commits once, below.
        db.flush()
        for position, name in enumerate(starter.categories):
            db.add(Category(group_id=group.id, name=name, sort_order=position))

    db.commit()
    return len(groups), sum(len(group.categories) for group in groups)


def check_tree(tree: list[StarterGroup]) -> None:
    """The rules the database would enforce, checked before anything is written.

    They can't be left to the inserts: autoflush is off, so a query during the
    writes can't see the rows the same transaction has pending. Each name is
    also its own column width.
    """
    if sum(1 for group in tree if group.is_income) > 1:
        raise CategoryError("The starter tree has more than one income group.")

    seen_groups: set[str] = set()
    for group in tree:
        _check_name(group.name, "group")
        if group.name in seen_groups:
            raise CategoryError(f'The starter tree lists "{group.name}" twice.')
        seen_groups.add(group.name)

        seen_categories: set[str] = set()
        for category in group.categories:
            _check_name(category, f'category in "{group.name}"')
            if category in seen_categories:
                raise CategoryError(
                    f'The starter tree lists "{category}" twice in "{group.name}".'
                )
            seen_categories.add(category)


def _check_name(name: str, what: str) -> None:
    if not name.strip() or len(name) > NAME_MAX_LENGTH:
        raise CategoryError(f'"{name}" is not a usable name for a {what}.')


def _clear(db: Session) -> None:
    """Empty the tree. The API deliberately can't do this: hiding is the
    archive (plan 03 C1)."""
    db.execute(delete(Category))
    db.execute(delete(CategoryGroup))
    db.flush()

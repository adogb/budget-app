"""The category tree: queries, and the rules a change has to pass.

Ordering is an integer per row, and the order endpoints take the whole list in
its new order, so a reorder is one statement per row and never a half-applied
swap (plan 03 C2). Nothing here deletes: hiding is the archive (C1).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.categories.errors import CategoryError, CategoryNotFoundError
from app.models import Category, CategoryGroup


def list_groups(db: Session) -> list[CategoryGroup]:
    """Every group in order, each with its categories in order.

    Hidden rows come back too: the page decides what to show, and the tree is
    small enough to send whole.
    """
    query = (
        select(CategoryGroup)
        .options(selectinload(CategoryGroup.categories))
        .order_by(CategoryGroup.sort_order, CategoryGroup.id)
    )
    return list(db.scalars(query))


def get_group(db: Session, group_id: int) -> CategoryGroup:
    group = db.get(CategoryGroup, group_id)
    if group is None:
        raise CategoryNotFoundError(f"No category group with id {group_id}.")
    return group


def get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise CategoryNotFoundError(f"No category with id {category_id}.")
    return category


def create_group(db: Session, name: str, is_income: bool = False) -> CategoryGroup:
    _check_group_name(db, name)
    if is_income:
        _check_income_group_is_free(db, group_id=None)
    group = CategoryGroup(
        name=name, is_income=is_income, sort_order=_next_group_order(db)
    )
    db.add(group)
    db.commit()
    return group


def update_group(
    db: Session,
    group_id: int,
    *,
    name: str | None = None,
    hidden: bool | None = None,
    is_income: bool | None = None,
) -> CategoryGroup:
    """Only the fields given change. Everything is checked before anything is
    written, so a refused change leaves the row as it was."""
    group = get_group(db, group_id)
    new_name = group.name if name is None else name
    new_is_income = group.is_income if is_income is None else is_income
    new_hidden = group.hidden if hidden is None else hidden

    if new_name != group.name:
        _check_group_name(db, new_name)
    if new_is_income and not group.is_income:
        _check_income_group_is_free(db, group_id=group.id)
    if new_hidden and new_is_income:
        raise CategoryError("The income group can't be hidden.")

    group.name = new_name
    group.is_income = new_is_income
    group.hidden = new_hidden
    db.commit()
    return group


def create_category(db: Session, group_id: int, name: str) -> Category:
    get_group(db, group_id)
    _check_category_name(db, group_id, name)
    category = Category(
        group_id=group_id, name=name, sort_order=_next_category_order(db, group_id)
    )
    db.add(category)
    db.commit()
    return category


def update_category(
    db: Session,
    category_id: int,
    *,
    name: str | None = None,
    hidden: bool | None = None,
) -> Category:
    category = get_category(db, category_id)
    new_name = category.name if name is None else name

    if new_name != category.name:
        _check_category_name(db, category.group_id, new_name)

    category.name = new_name
    if hidden is not None:
        category.hidden = hidden
    db.commit()
    return category


def reorder_groups(db: Session, ids: list[int]) -> None:
    """Put the groups in this order. `ids` must be every group, exactly once."""
    groups = {group.id: group for group in db.scalars(select(CategoryGroup))}
    if set(ids) != set(groups) or len(ids) != len(groups):
        raise CategoryError(
            "The order must list every category group exactly once. "
            "Refresh the page and try again."
        )
    for position, group_id in enumerate(ids):
        groups[group_id].sort_order = position
    db.commit()


def reorder_categories(db: Session, group_id: int, ids: list[int]) -> None:
    """Put this group's categories in this order. `ids` must be every one of
    them, exactly once, and none from another group."""
    get_group(db, group_id)
    categories = {
        category.id: category
        for category in db.scalars(
            select(Category).where(Category.group_id == group_id)
        )
    }
    if set(ids) != set(categories) or len(ids) != len(categories):
        raise CategoryError(
            "The order must list every category in this group exactly once. "
            "Refresh the page and try again."
        )
    for position, category_id in enumerate(ids):
        categories[category_id].sort_order = position
    db.commit()


def _check_group_name(db: Session, name: str) -> None:
    if db.scalar(select(CategoryGroup).where(CategoryGroup.name == name)) is not None:
        raise CategoryError(f'There is already a group called "{name}".')


def _check_category_name(db: Session, group_id: int, name: str) -> None:
    existing = db.scalar(
        select(Category).where(Category.group_id == group_id, Category.name == name)
    )
    if existing is not None:
        raise CategoryError(
            f'There is already a category called "{name}" in this group, '
            "possibly hidden."
        )


def _check_income_group_is_free(db: Session, group_id: int | None) -> None:
    """Only one group can be the income group (plan 03 C3)."""
    query = select(CategoryGroup).where(CategoryGroup.is_income.is_(True))
    if group_id is not None:
        query = query.where(CategoryGroup.id != group_id)
    other = db.scalar(query)
    if other is not None:
        raise CategoryError(
            f'"{other.name}" is already the income group. Turn that off first.'
        )


def _next_group_order(db: Session) -> int:
    """One past the highest group order, so a new group lands at the end."""
    top = db.scalar(select(func.max(CategoryGroup.sort_order)))
    return 0 if top is None else top + 1


def _next_category_order(db: Session, group_id: int) -> int:
    top = db.scalar(
        select(func.max(Category.sort_order)).where(Category.group_id == group_id)
    )
    return 0 if top is None else top + 1

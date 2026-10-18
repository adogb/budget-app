from typing import Self

from pydantic import BaseModel

from app.models import Category, CategoryGroup


class CategoryOut(BaseModel):
    id: int
    group_id: int
    name: str
    hidden: bool
    sort_order: int

    @classmethod
    def from_model(cls, category: Category) -> Self:
        return cls(
            id=category.id,
            group_id=category.group_id,
            name=category.name,
            hidden=category.hidden,
            sort_order=category.sort_order,
        )


class CategoryGroupOut(BaseModel):
    """A group with its categories, both already in order. Hidden rows are
    included; the page decides whether to show them."""

    id: int
    name: str
    is_income: bool
    hidden: bool
    sort_order: int
    categories: list[CategoryOut]

    @classmethod
    def from_model(cls, group: CategoryGroup) -> Self:
        return cls(
            id=group.id,
            name=group.name,
            is_income=group.is_income,
            hidden=group.hidden,
            sort_order=group.sort_order,
            categories=[CategoryOut.from_model(c) for c in group.categories],
        )


class GroupIn(BaseModel):
    name: str
    is_income: bool = False


class GroupPatch(BaseModel):
    """Only the fields sent are changed."""

    name: str | None = None
    hidden: bool | None = None
    is_income: bool | None = None


class CategoryIn(BaseModel):
    group_id: int
    name: str


class CategoryPatch(BaseModel):
    name: str | None = None
    hidden: bool | None = None


class OrderIn(BaseModel):
    """The ids in their new order, complete and without repeats."""

    ids: list[int]

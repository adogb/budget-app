from fastapi import APIRouter

from app.categories import service
from app.categories.schemas import (
    CategoryGroupOut,
    CategoryIn,
    CategoryOut,
    CategoryPatch,
    GroupIn,
    GroupPatch,
    OrderIn,
)
from app.db import DbSession

groups_router = APIRouter(prefix="/api/category-groups", tags=["categories"])
categories_router = APIRouter(prefix="/api/categories", tags=["categories"])


@groups_router.get("")
def get_groups(db: DbSession) -> list[CategoryGroupOut]:
    """The whole tree, in order, hidden rows included."""
    return [CategoryGroupOut.from_model(group) for group in service.list_groups(db)]


@groups_router.post("", status_code=201)
def create_group(db: DbSession, body: GroupIn) -> CategoryGroupOut:
    return CategoryGroupOut.from_model(
        service.create_group(db, body.name, body.is_income)
    )


@groups_router.patch("/{group_id}")
def update_group(db: DbSession, group_id: int, body: GroupPatch) -> CategoryGroupOut:
    group = service.update_group(
        db, group_id, name=body.name, hidden=body.hidden, is_income=body.is_income
    )
    return CategoryGroupOut.from_model(group)


@groups_router.put("/order", status_code=204)
def reorder_groups(db: DbSession, body: OrderIn) -> None:
    service.reorder_groups(db, body.ids)


@groups_router.put("/{group_id}/categories/order", status_code=204)
def reorder_categories(db: DbSession, group_id: int, body: OrderIn) -> None:
    service.reorder_categories(db, group_id, body.ids)


@categories_router.post("", status_code=201)
def create_category(db: DbSession, body: CategoryIn) -> CategoryOut:
    return CategoryOut.from_model(service.create_category(db, body.group_id, body.name))


@categories_router.patch("/{category_id}")
def update_category(
    db: DbSession, category_id: int, body: CategoryPatch
) -> CategoryOut:
    category = service.update_category(
        db, category_id, name=body.name, hidden=body.hidden
    )
    return CategoryOut.from_model(category)

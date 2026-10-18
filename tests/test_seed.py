import pytest

from app.categories import service
from app.categories.errors import CategoryError
from app.categories.seed import StarterGroup, apply_starter_tree, load_starter_tree


def test_loads_the_starter_tree(db):
    groups, categories = apply_starter_tree(db)

    assert (groups, categories) == (14, 68)
    tree = service.list_groups(db)
    assert tree[0].name == "Income"
    assert tree[0].is_income is True
    assert len(tree[0].categories) == 6
    assert [group.name for group in tree][-1] == "Other"
    assert sum(1 for group in tree if group.is_income) == 1


def test_order_follows_the_file(db):
    apply_starter_tree(db)

    tree = service.list_groups(db)

    assert [group.sort_order for group in tree] == list(range(14))
    for group in tree:
        assert [c.sort_order for c in group.categories] == list(
            range(len(group.categories))
        )


def test_the_reorg_is_applied(db):
    apply_starter_tree(db)
    groups = {group.name: group for group in service.list_groups(db)}

    def names(group_name):
        return [category.name for category in groups[group_name].categories]

    assert names("Food and drinks")[0] == "Groceries"  # R1

    assert names("Other") == [  # R2
        "Cash withdrawal / deposit",
        "Other expense",
        "Unknown expense",
    ]
    assert names("Loans")[:2] == ["Realkredit loan", "Bank loan"]  # R3
    assert "Home and utilities" not in groups  # R4
    home = names("Home, bills and utilities")
    assert {"Phone & internet", "TV services"} <= set(home)
    assert "Realkredit loan" not in home


def test_food_and_drinks_twice_is_fine(db):
    apply_starter_tree(db)
    groups = {group.name: group for group in service.list_groups(db)}

    assert "Food and drinks" in groups
    assert "Food and drinks" in [
        category.name for category in groups["Travel"].categories
    ]


def test_refuses_a_non_empty_database(db):
    apply_starter_tree(db)

    with pytest.raises(CategoryError, match="already has category groups"):
        apply_starter_tree(db)

    assert len(service.list_groups(db)) == 14
    assert sum(len(group.categories) for group in service.list_groups(db)) == 68


def test_replace_starts_over(db):
    apply_starter_tree(db)
    service.create_group(db, "Something I added", is_income=False)
    service.create_category(db, service.list_groups(db)[0].id, "Something else")

    groups, categories = apply_starter_tree(db, replace=True)

    assert (groups, categories) == (14, 68)
    assert next(group.name for group in service.list_groups(db)) == "Income"
    assert "Something I added" not in [group.name for group in service.list_groups(db)]


def test_a_second_income_group_is_refused_before_writing(db):
    tree = [
        StarterGroup(name="One", is_income=True, categories=["A"]),
        StarterGroup(name="Two", is_income=True, categories=["B"]),
    ]

    with pytest.raises(CategoryError, match="more than one income group"):
        apply_starter_tree(db, tree)

    assert service.list_groups(db) == []


def test_a_duplicate_in_the_file_is_refused_before_writing(db):
    tree = [
        StarterGroup(name="Housing", categories=["Rent", "Rent"]),
    ]

    with pytest.raises(CategoryError, match="twice"):
        apply_starter_tree(db, tree)

    assert service.list_groups(db) == []


def test_a_bad_file_does_not_clear_a_good_tree(db):
    apply_starter_tree(db)
    bad = [StarterGroup(name="", categories=[])]

    with pytest.raises(CategoryError):
        apply_starter_tree(db, bad, replace=True)

    assert len(service.list_groups(db)) == 14


def test_starter_file_has_no_stray_internal_row(db):
    tree = load_starter_tree()

    names = [category for group in tree for category in group.categories]
    assert "Internal transfers" not in names

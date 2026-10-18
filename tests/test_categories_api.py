from app.models import Category, CategoryGroup


def add_group(
    db, name, *, is_income=False, hidden=False, sort_order=0
) -> CategoryGroup:
    group = CategoryGroup(
        name=name, is_income=is_income, hidden=hidden, sort_order=sort_order
    )
    db.add(group)
    db.commit()
    return group


def add_category(db, group, name, *, hidden=False, sort_order=0) -> Category:
    category = Category(
        group_id=group.id, name=name, hidden=hidden, sort_order=sort_order
    )
    db.add(category)
    db.commit()
    return category


def test_empty_tree(client):
    response = client.get("/api/category-groups")

    assert response.status_code == 200
    assert response.json() == []


def test_create_group_and_category(client):
    created = client.post("/api/category-groups", json={"name": "Housing"})

    assert created.status_code == 201
    group = created.json()
    assert group["name"] == "Housing"
    assert group["is_income"] is False
    assert group["hidden"] is False
    assert group["categories"] == []

    made = client.post(
        "/api/categories", json={"group_id": group["id"], "name": "Electricity"}
    )

    assert made.status_code == 201
    category = made.json()
    assert category["group_id"] == group["id"]
    assert category["name"] == "Electricity"
    assert client.get("/api/category-groups").json()[0]["categories"] == [category]


def test_tree_is_ordered(client, db):
    second = add_group(db, "Second", sort_order=1)
    add_group(db, "First", sort_order=0)
    add_category(db, second, "Later", sort_order=1)
    add_category(db, second, "Earlier", sort_order=0)

    tree = client.get("/api/category-groups").json()

    assert [group["name"] for group in tree] == ["First", "Second"]
    assert [c["name"] for c in tree[1]["categories"]] == ["Earlier", "Later"]


def test_rename_and_hide(client, db):
    group = add_group(db, "Housing")
    category = add_category(db, group, "Rent")

    renamed = client.patch(
        f"/api/category-groups/{group.id}", json={"name": "Home", "hidden": True}
    )
    hidden = client.patch(f"/api/categories/{category.id}", json={"hidden": True})

    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Home"
    assert renamed.json()["hidden"] is True
    assert hidden.status_code == 200
    assert hidden.json()["hidden"] is True

    # Hidden rows stay in the tree; the page decides whether to show them.
    tree = client.get("/api/category-groups").json()
    assert tree[0]["name"] == "Home"
    assert tree[0]["hidden"] is True
    assert tree[0]["categories"][0]["hidden"] is True


def test_names_are_trimmed(client):
    created = client.post("/api/category-groups", json={"name": "  Housing  "})

    assert created.json()["name"] == "Housing"


def test_duplicate_group_name_is_400(client, db):
    add_group(db, "Housing")

    response = client.post("/api/category-groups", json={"name": "Housing"})

    assert response.status_code == 400
    assert "Housing" in response.json()["detail"]


def test_duplicate_category_name_in_same_group_is_400(client, db):
    housing = add_group(db, "Housing")
    shopping = add_group(db, "Shopping")
    add_category(db, housing, "Other")

    same_group = client.post(
        "/api/categories", json={"group_id": housing.id, "name": "Other"}
    )
    other_group = client.post(
        "/api/categories", json={"group_id": shopping.id, "name": "Other"}
    )

    assert same_group.status_code == 400
    assert "Other" in same_group.json()["detail"]
    # The same name in another group is fine (the sheet has "Food and drinks"
    # twice, in exactly this way).
    assert other_group.status_code == 201


def test_moving_an_income_group(client, db):
    first = add_group(db, "Income", is_income=True)
    second = add_group(db, "Salary")

    refused = client.patch(
        f"/api/category-groups/{second.id}", json={"is_income": True}
    )

    assert refused.status_code == 400
    assert "Income" in refused.json()["detail"]

    client.patch(f"/api/category-groups/{first.id}", json={"is_income": False})
    moved = client.patch(f"/api/category-groups/{second.id}", json={"is_income": True})

    assert moved.status_code == 200
    assert moved.json()["is_income"] is True


def test_first_income_group_is_allowed(client):
    created = client.post(
        "/api/category-groups", json={"name": "Income", "is_income": True}
    )

    assert created.status_code == 201
    assert created.json()["is_income"] is True


def test_income_group_cannot_be_hidden(client, db):
    income = add_group(db, "Income", is_income=True)

    response = client.patch(f"/api/category-groups/{income.id}", json={"hidden": True})

    assert response.status_code == 400
    assert client.get("/api/category-groups").json()[0]["hidden"] is False


def test_blank_name_is_400(client, db):
    group = add_group(db, "Housing")

    for name in ["", "   "]:
        assert (
            client.post("/api/category-groups", json={"name": name}).status_code == 400
        )
        assert (
            client.post(
                "/api/categories", json={"group_id": group.id, "name": name}
            ).status_code
            == 400
        )
        assert (
            client.patch(
                f"/api/category-groups/{group.id}", json={"name": name}
            ).status_code
            == 400
        )

    assert client.get("/api/category-groups").json()[0]["name"] == "Housing"


def test_reorder_groups(client, db):
    housing = add_group(db, "Housing", sort_order=0)
    travel = add_group(db, "Travel", sort_order=1)
    shopping = add_group(db, "Shopping", sort_order=2)

    response = client.put(
        "/api/category-groups/order", json={"ids": [shopping.id, housing.id, travel.id]}
    )

    assert response.status_code == 204
    tree = client.get("/api/category-groups").json()
    assert [group["name"] for group in tree] == ["Shopping", "Housing", "Travel"]
    assert [group["sort_order"] for group in tree] == [0, 1, 2]


def test_reorder_rejects_a_partial_list(client, db):
    add_group(db, "Housing", sort_order=0)
    travel = add_group(db, "Travel", sort_order=1)

    response = client.put("/api/category-groups/order", json={"ids": [travel.id]})

    assert response.status_code == 400
    tree = client.get("/api/category-groups").json()
    assert [group["name"] for group in tree] == ["Housing", "Travel"]


def test_reorder_categories_is_scoped_to_the_group(client, db):
    housing = add_group(db, "Housing")
    travel = add_group(db, "Travel")
    rent = add_category(db, housing, "Rent", sort_order=0)
    flights = add_category(db, travel, "Flights", sort_order=0)

    response = client.put(
        f"/api/category-groups/{housing.id}/categories/order",
        json={"ids": [flights.id, rent.id]},
    )

    assert response.status_code == 400
    tree = client.get("/api/category-groups").json()
    assert [c["name"] for c in tree[0]["categories"]] == ["Rent"]


def test_patch_unknown_id_is_404(client):
    assert (
        client.patch("/api/category-groups/999", json={"name": "X"}).status_code == 404
    )
    assert client.patch("/api/categories/999", json={"name": "X"}).status_code == 404
    assert (
        client.post("/api/categories", json={"group_id": 999, "name": "X"}).status_code
        == 404
    )
    assert (
        client.put(
            "/api/category-groups/999/categories/order", json={"ids": []}
        ).status_code
        == 404
    )

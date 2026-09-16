"""Presets, custom tags, and the categories that sort them."""

from app.seed import RAINBOW


def test_seven_presets_one_per_rainbow_colour(auth):
    tags = auth.get("/api/tags").json()
    presets = [t for t in tags if t["is_preset"]]

    assert len(presets) == 7
    assert {t["color"] for t in presets} == set(RAINBOW.values())


def test_presets_are_split_across_two_categories(auth):
    categories = auth.get("/api/categories").json()
    by_name = {c["name"]: c for c in categories}

    # Status is exclusive: a book is reading OR read, never both.
    assert by_name["Status"]["exclusive"] is True
    assert len(by_name["Status"]["tags"]) == 4

    # Shelf is not: a book can be owned, lent and beloved at once.
    assert by_name["Shelf"]["exclusive"] is False
    assert len(by_name["Shelf"]["tags"]) == 3


def test_empty_categories_are_ready_for_the_user(auth):
    categories = {c["name"]: c for c in auth.get("/api/categories").json()}
    assert categories["Genre"]["tags"] == []
    assert categories["Mood"]["tags"] == []


def test_seeding_does_not_run_twice(auth):
    from app.database import SessionLocal
    from app.seed import seed_all

    db = SessionLocal()
    try:
        seed_all(db)
        seed_all(db)
    finally:
        db.close()

    assert len(auth.get("/api/tags").json()) == 7


def test_create_a_custom_tag(auth):
    category = auth.get("/api/categories").json()[2]["id"]
    response = auth.post(
        "/api/tags",
        json={"name": "Sea stories", "color": "#0E4A5E", "category_id": category},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sea stories"
    assert body["color"] == "#0e4a5e".lower()
    assert body["is_preset"] is False


def test_three_digit_hex_expands(auth):
    category = auth.get("/api/categories").json()[0]["id"]
    body = auth.post(
        "/api/tags", json={"name": "Teal", "color": "#0af", "category_id": category}
    ).json()
    assert body["color"] == "#00aaff"


def test_a_bad_colour_is_refused(auth):
    category = auth.get("/api/categories").json()[0]["id"]
    response = auth.post(
        "/api/tags", json={"name": "Nope", "color": "turquoise", "category_id": category}
    )
    assert response.status_code == 422


def test_duplicate_tag_names_are_refused(auth):
    category = auth.get("/api/categories").json()[0]["id"]
    payload = {"name": "Reading", "color": "#ffffff", "category_id": category}
    assert auth.post("/api/tags", json=payload).status_code == 409


def test_a_preset_can_be_renamed_and_recoloured(auth):
    tags = auth.get("/api/tags").json()
    reading = next(t for t in tags if t["role"] == "reading")

    response = auth.patch(
        f"/api/tags/{reading['id']}", json={"name": "Leyendo", "color": "#ff00aa"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Leyendo"
    assert body["color"] == "#ff00aa"
    # The machine-readable role survives the rename, which is the whole point.
    assert body["role"] == "reading"


def test_a_tag_can_move_between_categories(auth):
    categories = auth.get("/api/categories").json()
    genre = next(c for c in categories if c["name"] == "Genre")
    favourite = next(
        t for c in categories for t in c["tags"] if t["role"] == "favourite"
    )

    body = auth.patch(
        f"/api/tags/{favourite['id']}", json={"category_id": genre["id"]}
    ).json()
    assert body["category_id"] == genre["id"]


def test_deleting_a_tag_leaves_its_books_alone(auth):
    tags = auth.get("/api/tags").json()
    owned = next(t for t in tags if t["role"] == "owned")

    book = auth.post(
        "/api/books", json={"title": "Jaws", "tag_ids": [owned["id"]]}
    ).json()
    assert len(book["tags"]) == 1

    assert auth.delete(f"/api/tags/{owned['id']}").status_code == 204

    after = auth.get(f"/api/books/{book['id']}").json()
    assert after["title"] == "Jaws"
    assert after["tags"] == []


def test_book_counts_are_reported(auth):
    tags = auth.get("/api/tags").json()
    owned = next(t for t in tags if t["role"] == "owned")

    for title in ("One", "Two", "Three"):
        auth.post("/api/books", json={"title": title, "tag_ids": [owned["id"]]})

    refreshed = next(t for t in auth.get("/api/tags").json() if t["role"] == "owned")
    assert refreshed["book_count"] == 3


def test_create_and_delete_a_category(auth):
    created = auth.post(
        "/api/categories",
        json={"name": "Format", "description": "Paper, ebook, audio", "exclusive": True},
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    auth.post(
        "/api/tags",
        json={"name": "Audiobook", "color": "#5cd68a", "category_id": category_id},
    )

    assert auth.delete(f"/api/categories/{category_id}").status_code == 204
    # Deleting a category takes its tags with it.
    assert not any(t["name"] == "Audiobook" for t in auth.get("/api/tags").json())


def test_duplicate_category_names_are_refused(auth):
    assert (
        auth.post("/api/categories", json={"name": "status"}).status_code == 409
    )


def test_reorder_tags(auth):
    tags = auth.get("/api/tags").json()
    order = [t["id"] for t in tags][::-1]
    body = auth.post("/api/tags/reorder", json=order).json()
    assert [t["id"] for t in body] == order
    assert [t["position"] for t in body] == list(range(len(order)))


def test_tag_on_a_missing_category_is_404(auth):
    response = auth.post(
        "/api/tags", json={"name": "Ghost", "color": "#ffffff", "category_id": 9999}
    )
    assert response.status_code == 404

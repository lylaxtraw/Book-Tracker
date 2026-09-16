from app.seed import RAINBOW


def test_seven_presets_one_per_rainbow_colour(tags):
    presets = [t for t in tags.values() if t["is_preset"]]
    assert len(presets) == 7
    assert {t["color"] for t in presets} == {c.upper() for c in RAINBOW.values()}


def test_presets_land_in_their_categories(client):
    categories = {c["name"]: c for c in client.get("/api/categories").json()}
    assert {t["name"] for t in categories["Status"]["tags"]} == {
        "Want to read", "Reading", "Read", "Gave up"
    }
    assert {t["name"] for t in categories["Shelf"]["tags"]} == {
        "Owned", "Wishlist", "Borrowed"
    }


def test_status_is_exclusive_and_shelf_is_not(client):
    categories = {c["name"]: c for c in client.get("/api/categories").json()}
    assert categories["Status"]["exclusive"] is True
    assert categories["Shelf"]["exclusive"] is False


def test_seeding_twice_changes_nothing(db, client):
    from app.seed import seed_presets

    before = len(client.get("/api/tags").json())
    seed_presets(db)
    assert len(client.get("/api/tags").json()) == before


def test_create_a_custom_tag(client):
    category = client.get("/api/categories").json()[0]
    response = client.post(
        "/api/tags",
        json={"name": "Shark books", "color": "#1B7A8C", "category_id": category["id"]},
    )
    assert response.status_code == 201
    assert response.json()["color"] == "#1B7A8C"
    assert response.json()["is_preset"] is False


def test_duplicate_tag_names_are_refused(client, tags):
    response = client.post(
        "/api/tags",
        json={"name": "Reading", "color": "#FFC65C",
              "category_id": tags["Reading"]["category_id"]},
    )
    assert response.status_code == 409


def test_colour_must_be_hex(client):
    category = client.get("/api/categories").json()[0]
    response = client.post(
        "/api/tags",
        json={"name": "Bad", "color": "purple", "category_id": category["id"]},
    )
    assert response.status_code == 422


def test_rename_and_recolour_a_preset(client, tags):
    tag_id = tags["Gave up"]["id"]
    response = client.patch(
        f"/api/tags/{tag_id}", json={"name": "Abandoned", "color": "#aa0044"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Abandoned"
    assert response.json()["color"] == "#AA0044"


def test_move_a_tag_to_another_category(client, tags):
    categories = {c["name"]: c for c in client.get("/api/categories").json()}
    response = client.patch(
        f"/api/tags/{tags['Borrowed']['id']}",
        json={"category_id": categories["My tags"]["id"]},
    )
    assert response.json()["category_id"] == categories["My tags"]["id"]


def test_delete_a_tag(client, tags):
    assert client.delete(f"/api/tags/{tags['Wishlist']['id']}").status_code == 204
    assert "Wishlist" not in {t["name"] for t in client.get("/api/tags").json()}


def test_new_categories_can_be_made_and_removed(client):
    created = client.post(
        "/api/categories", json={"name": "Mood", "exclusive": True}
    )
    assert created.status_code == 201
    assert created.json()["exclusive"] is True
    assert client.delete(f"/api/categories/{created.json()['id']}").status_code == 204


def test_preset_categories_cannot_be_deleted(client):
    categories = {c["name"]: c for c in client.get("/api/categories").json()}
    response = client.delete(f"/api/categories/{categories['Status']['id']}")
    assert response.status_code == 400


def test_deleting_a_category_takes_its_tags_with_it(client):
    category = client.post("/api/categories", json={"name": "Temp"}).json()
    client.post(
        "/api/tags",
        json={"name": "Scratch", "color": "#3DBE7C", "category_id": category["id"]},
    )
    client.delete(f"/api/categories/{category['id']}")
    assert "Scratch" not in {t["name"] for t in client.get("/api/tags").json()}


def test_unknown_tag_returns_404(client):
    assert client.patch("/api/tags/9999", json={"name": "Nope"}).status_code == 404

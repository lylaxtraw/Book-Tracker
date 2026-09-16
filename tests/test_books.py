"""Books: creating them, tagging them, and the rules that fire when you do."""

from datetime import date

from conftest import make_book


def test_an_empty_library(auth):
    body = auth.get("/api/books").json()
    assert body == {"items": [], "total": 0, "limit": 60, "offset": 0}


def test_create_a_book(auth):
    book = make_book(auth, "Moby-Dick", authors="Herman Melville", page_count=635)
    assert book["title"] == "Moby-Dick"
    assert book["source"] == "manual"
    assert book["progress_percent"] == 0.0
    assert book["tags"] == []


def test_a_title_is_required(auth):
    assert auth.post("/api/books", json={"authors": "Nobody"}).status_code == 422


def test_ratings_must_land_on_a_half_star(auth):
    assert auth.post(
        "/api/books", json={"title": "Off", "rating": 3.3}
    ).status_code == 422
    assert auth.post(
        "/api/books", json={"title": "On", "rating": 3.5}
    ).status_code == 201


def test_ratings_cannot_exceed_five(auth):
    assert auth.post(
        "/api/books", json={"title": "Too good", "rating": 6}
    ).status_code == 422


def test_progress_is_derived_from_pages(auth):
    book = make_book(auth, "Long one", page_count=300)
    updated = auth.patch(f"/api/books/{book['id']}", json={"current_page": 75}).json()
    assert updated["progress_percent"] == 25.0


def test_progress_without_a_page_count_stays_zero(auth):
    book = make_book(auth, "Unknown length")
    updated = auth.patch(f"/api/books/{book['id']}", json={"current_page": 40}).json()
    assert updated["progress_percent"] == 0.0


def test_progress_cannot_run_past_the_last_page(auth):
    book = make_book(auth, "Short", page_count=100)
    updated = auth.post(f"/api/books/{book['id']}/progress?current_page=400").json()
    assert updated["current_page"] == 100
    assert updated["progress_percent"] == 100.0


def test_exclusive_categories_reject_two_tags_at_once(auth, tags):
    response = auth.post(
        "/api/books",
        json={
            "title": "Confused",
            "tag_ids": [tags["reading"]["id"], tags["finished"]["id"]],
        },
    )
    assert response.status_code == 400
    assert "one tag per book" in response.json()["detail"]


def test_a_book_can_be_owned_and_read_at_once(auth, tags):
    book = auth.post(
        "/api/books",
        json={
            "title": "Both",
            "tag_ids": [tags["owned"]["id"], tags["finished"]["id"]],
        },
    ).json()
    assert {t["role"] for t in book["tags"]} == {"owned", "finished"}


def test_the_whole_shelf_category_can_apply_together(auth, tags):
    book = auth.post(
        "/api/books",
        json={
            "title": "Beloved and lent",
            "tag_ids": [
                tags["owned"]["id"],
                tags["lent"]["id"],
                tags["favourite"]["id"],
            ],
        },
    ).json()
    assert len(book["tags"]) == 3


def test_unknown_tag_ids_are_404(auth):
    response = auth.post("/api/books", json={"title": "Ghost", "tag_ids": [4242]})
    assert response.status_code == 404


def test_marking_it_read_stamps_a_finish_date(auth, tags):
    book = auth.post(
        "/api/books",
        json={"title": "Done", "page_count": 200, "tag_ids": [tags["finished"]["id"]]},
    ).json()
    assert book["date_finished"] == date.today().isoformat()
    assert book["current_page"] == 200
    assert book["progress_percent"] == 100.0


def test_marking_it_reading_stamps_a_start_date(auth, tags):
    book = auth.post(
        "/api/books",
        json={"title": "Underway", "tag_ids": [tags["reading"]["id"]]},
    ).json()
    assert book["date_started"] == date.today().isoformat()
    assert book["date_finished"] is None


def test_a_hand_typed_date_is_not_overwritten(auth, tags):
    book = auth.post(
        "/api/books",
        json={
            "title": "Finished long ago",
            "date_finished": "2019-04-02",
            "tag_ids": [tags["finished"]["id"]],
        },
    ).json()
    assert book["date_finished"] == "2019-04-02"


def test_moving_back_to_reading_clears_the_finish_date(auth, tags):
    book = auth.post(
        "/api/books", json={"title": "Restart", "tag_ids": [tags["finished"]["id"]]}
    ).json()
    assert book["date_finished"] is not None

    moved = auth.patch(
        f"/api/books/{book['id']}", json={"tag_ids": [tags["reading"]["id"]]}
    ).json()
    assert moved["date_finished"] is None


def test_an_untagged_book_keeps_its_dates(auth, tags):
    book = auth.post(
        "/api/books",
        json={"title": "Loose", "date_finished": "2020-01-01", "tag_ids": []},
    ).json()
    assert book["date_finished"] == "2020-01-01"


def test_update_and_delete(auth):
    book = make_book(auth, "Draft")
    updated = auth.patch(
        f"/api/books/{book['id']}", json={"title": "Final", "notes": "Loved it."}
    ).json()
    assert updated["title"] == "Final"
    assert updated["notes"] == "Loved it."

    assert auth.delete(f"/api/books/{book['id']}").status_code == 204
    assert auth.get(f"/api/books/{book['id']}").status_code == 404


def test_unknown_fields_are_refused_on_update(auth):
    book = make_book(auth)
    response = auth.patch(f"/api/books/{book['id']}", json={"colour": "blue"})
    assert response.status_code == 422


def test_free_text_search_covers_title_and_author(auth):
    make_book(auth, "The Old Man and the Sea", authors="Ernest Hemingway")
    make_book(auth, "Blue Ocean Strategy", authors="W. Chan Kim")

    assert auth.get("/api/books?q=ocean").json()["total"] == 1
    assert auth.get("/api/books?q=hemingway").json()["total"] == 1
    assert auth.get("/api/books?q=SEA").json()["total"] == 1
    assert auth.get("/api/books?q=nothing").json()["total"] == 0


def test_filter_by_any_tag(auth, tags):
    auth.post("/api/books", json={"title": "A", "tag_ids": [tags["owned"]["id"]]})
    auth.post("/api/books", json={"title": "B", "tag_ids": [tags["wishlist"]["id"]]})

    body = auth.get(f"/api/books?tag_ids={tags['owned']['id']}").json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "A"


def test_filter_by_all_tags(auth, tags):
    auth.post(
        "/api/books",
        json={
            "title": "Both",
            "tag_ids": [tags["owned"]["id"], tags["favourite"]["id"]],
        },
    )
    auth.post("/api/books", json={"title": "One", "tag_ids": [tags["owned"]["id"]]})

    query = (
        f"/api/books?tag_ids={tags['owned']['id']}"
        f"&tag_ids={tags['favourite']['id']}&match=all"
    )
    body = auth.get(query).json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Both"


def test_filter_untagged(auth, tags):
    auth.post("/api/books", json={"title": "Tagged", "tag_ids": [tags["owned"]["id"]]})
    make_book(auth, "Bare")

    body = auth.get("/api/books?untagged=true").json()
    assert [b["title"] for b in body["items"]] == ["Bare"]


def test_sort_by_title(auth):
    for title in ("Zebra", "apple", "Mango"):
        make_book(auth, title)
    titles = [b["title"] for b in auth.get("/api/books?sort=title").json()["items"]]
    assert titles == ["apple", "Mango", "Zebra"]


def test_sort_by_rating_puts_unrated_last(auth):
    make_book(auth, "Great", rating=5)
    make_book(auth, "Fine", rating=3)
    make_book(auth, "Unrated")

    titles = [b["title"] for b in auth.get("/api/books?sort=rating").json()["items"]]
    assert titles[:2] == ["Great", "Fine"]
    assert titles[-1] == "Unrated"


def test_pagination(auth):
    for i in range(12):
        make_book(auth, f"Book {i:02d}")
    body = auth.get("/api/books?limit=5&offset=5&sort=title").json()
    assert body["total"] == 12
    assert len(body["items"]) == 5
    assert body["offset"] == 5


def test_minimum_rating_filter(auth):
    make_book(auth, "Loved", rating=4.5)
    make_book(auth, "Fine", rating=2.0)
    body = auth.get("/api/books?min_rating=4").json()
    assert [b["title"] for b in body["items"]] == ["Loved"]

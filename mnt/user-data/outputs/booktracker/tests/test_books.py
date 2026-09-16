from datetime import date

from .conftest import make_book


def test_add_a_book(client):
    book = make_book(client, title="Jaws", author="Peter Benchley", year=1974)
    assert book["title"] == "Jaws"
    assert book["progress_percent"] == 0
    assert book["tags"] == []


def test_a_title_is_required(client):
    assert client.post("/api/books", json={"author": "Nobody"}).status_code == 422
    assert client.post("/api/books", json={"title": ""}).status_code == 422


def test_add_with_tags(client, tags):
    book = make_book(
        client, tag_ids=[tags["Owned"]["id"], tags["Reading"]["id"]]
    )
    assert {t["name"] for t in book["tags"]} == {"Owned", "Reading"}


def test_exclusive_category_keeps_only_one_status(client, tags):
    """Picking Read while Reading is on should not leave both attached."""
    book = make_book(
        client,
        tag_ids=[tags["Reading"]["id"], tags["Read"]["id"], tags["Owned"]["id"]],
    )
    statuses = [t["name"] for t in book["tags"] if t["name"] in
                {"Want to read", "Reading", "Read", "Gave up"}]
    assert len(statuses) == 1
    assert "Owned" in {t["name"] for t in book["tags"]}


def test_non_exclusive_tags_stack(client, tags):
    book = make_book(
        client, tag_ids=[tags["Owned"]["id"], tags["Borrowed"]["id"]]
    )
    assert len(book["tags"]) == 2


def test_unknown_tag_id_is_rejected(client):
    response = client.post("/api/books", json={"title": "Ghost", "tag_ids": [4242]})
    assert response.status_code == 400
    assert "4242" in response.json()["detail"]


def test_update_a_book(client):
    book = make_book(client)
    response = client.patch(
        f"/api/books/{book['id']}", json={"rating": 4.5, "notes": "Quietly devastating"}
    )
    assert response.json()["rating"] == 4.5
    assert response.json()["notes"] == "Quietly devastating"


def test_rating_is_capped_at_five(client):
    book = make_book(client)
    assert client.patch(f"/api/books/{book['id']}", json={"rating": 9}).status_code == 422


def test_progress_percent_is_derived(client):
    book = make_book(client, pages=200, progress_pages=50)
    assert book["progress_percent"] == 25


def test_progress_cannot_exceed_the_page_count(client):
    book = make_book(client, pages=100, progress_pages=400)
    assert book["progress_pages"] == 100
    assert book["progress_percent"] == 100


def test_finishing_a_book_completes_its_progress(client):
    book = make_book(client, pages=300, finished_on="2026-03-01")
    assert book["progress_pages"] == 300
    assert book["progress_percent"] == 100


def test_starting_a_book_stamps_the_start_date(client):
    book = make_book(client, pages=300, progress_pages=12)
    assert book["started_on"] == date.today().isoformat()


def test_a_book_with_no_page_count_reports_zero_percent(client):
    book = make_book(client, progress_pages=40)
    assert book["progress_percent"] == 0


def test_replacing_tags_on_update(client, tags):
    book = make_book(client, tag_ids=[tags["Want to read"]["id"]])
    updated = client.patch(
        f"/api/books/{book['id']}", json={"tag_ids": [tags["Read"]["id"]]}
    ).json()
    assert [t["name"] for t in updated["tags"]] == ["Read"]


def test_omitting_tag_ids_leaves_tags_alone(client, tags):
    book = make_book(client, tag_ids=[tags["Owned"]["id"]])
    updated = client.patch(f"/api/books/{book['id']}", json={"year": 1952}).json()
    assert [t["name"] for t in updated["tags"]] == ["Owned"]


def test_text_filter_matches_title_and_author(client):
    make_book(client, title="Jaws", author="Peter Benchley")
    make_book(client, title="Blue Ocean", author="Sylvia Earle")

    assert len(client.get("/api/books", params={"q": "jaws"}).json()) == 1
    assert len(client.get("/api/books", params={"q": "earle"}).json()) == 1
    assert len(client.get("/api/books", params={"q": "zzz"}).json()) == 0


def test_filter_by_tag_any_versus_all(client, tags):
    make_book(client, title="A", tag_ids=[tags["Owned"]["id"]])
    make_book(client, title="B",
              tag_ids=[tags["Owned"]["id"], tags["Borrowed"]["id"]])

    both = [tags["Owned"]["id"], tags["Borrowed"]["id"]]
    any_hits = client.get("/api/books", params=[("tag", t) for t in both]
                          + [("match", "any")]).json()
    all_hits = client.get("/api/books", params=[("tag", t) for t in both]
                          + [("match", "all")]).json()

    assert len(any_hits) == 2
    assert [b["title"] for b in all_hits] == ["B"]


def test_sorting_by_title(client):
    make_book(client, title="Zebra")
    make_book(client, title="Anchor")
    titles = [b["title"] for b in client.get("/api/books", params={"sort": "title"}).json()]
    assert titles == ["Anchor", "Zebra"]


def test_delete_a_book(client):
    book = make_book(client)
    assert client.delete(f"/api/books/{book['id']}").status_code == 204
    assert client.get(f"/api/books/{book['id']}").status_code == 404


def test_missing_book_returns_404(client):
    assert client.get("/api/books/777").status_code == 404
    assert client.delete("/api/books/777").status_code == 404

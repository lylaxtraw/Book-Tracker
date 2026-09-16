import csv
import io
import json

from .conftest import make_book


def upload(auth, text):
    return auth.post(
        "/api/import/csv",
        files={"file": ("shelf.csv", text.encode("utf-8"), "text/csv")},
    )


def rows_of(csv_text):
    return list(csv.DictReader(io.StringIO(csv_text)))


# ------------------------------------------------------------------- exporting


def test_export_has_headers_even_when_empty(auth):
    response = auth.get("/api/export/csv")
    assert response.status_code == 200
    assert "title" in response.text.splitlines()[0]


def test_export_includes_books_and_their_tags(auth, tags):
    make_book(
        auth,
        title="Jaws",
        authors="Peter Benchley",
        page_count=311,
        tag_ids=[tags["owned"]["id"], tags["finished"]["id"]],
    )

    row = rows_of(auth.get("/api/export/csv").text)[0]
    assert row["title"] == "Jaws"
    assert row["page_count"] == "311"
    assert set(row["tags"].split("; ")) == {"Owned", "Read"}


def test_export_offers_a_filename(auth):
    disposition = auth.get("/api/export/csv").headers["content-disposition"]
    assert "attachment" in disposition
    assert ".csv" in disposition


def test_json_backup_carries_tags_colours_and_goals(auth, tags):
    auth.put("/api/goals", json={"year": 2026, "target_books": 20})
    make_book(auth, title="Jaws", tag_ids=[tags["owned"]["id"]])

    backup = json.loads(auth.get("/api/export/json").text)
    assert backup["version"] == 1
    assert backup["books"][0]["tags"] == ["Owned"]
    assert backup["goals"][0]["target_books"] == 20
    assert any(
        t["name"] == "Owned" and t["color"] == "#5cd68a"
        for c in backup["categories"]
        for t in c["tags"]
    )


# ------------------------------------------------------------------- importing


def test_import_adds_books(auth):
    response = upload(auth, "title,author,pages\nJaws,Peter Benchley,311\n")
    assert response.json()["created"] == 1
    assert response.json()["skipped"] == 0
    assert auth.get("/api/books").json()["items"][0]["title"] == "Jaws"


def test_import_creates_tags_it_has_never_seen(auth):
    upload(auth, "title,tags\nJaws,Sharks; Owned\n")
    names = {t["name"] for t in auth.get("/api/tags").json()}
    assert "Sharks" in names

    new_tag = next(t for t in auth.get("/api/tags").json() if t["name"] == "Sharks")
    categories = {c["id"]: c["name"] for c in auth.get("/api/categories").json()}
    assert categories[new_tag["category_id"]] == "Imported"


def test_import_reuses_existing_tags_whatever_the_casing(auth):
    upload(auth, "title,tags\nJaws,owned\n")
    owned = [t for t in auth.get("/api/tags").json() if t["name"].lower() == "owned"]
    assert len(owned) == 1


def test_import_skips_books_already_on_the_shelf(auth):
    make_book(auth, title="Jaws", authors="Peter Benchley")
    response = upload(auth, "title,author\nJaws,Peter Benchley\n")
    assert response.json()["created"] == 0
    assert response.json()["skipped"] == 1


def test_import_skips_rows_with_no_title(auth):
    response = upload(auth, "title,author\n,Nobody\nJaws,Benchley\n")
    assert response.json()["created"] == 1
    assert response.json()["skipped"] == 1


def test_import_survives_junk_in_number_columns(auth):
    upload(auth, "title,pages,rating,year\nJaws,many,great,recently\n")
    book = auth.get("/api/books").json()["items"][0]
    assert book["page_count"] is None
    assert book["rating"] is None
    assert book["published_year"] is None


def test_import_survives_a_bad_date(auth):
    upload(auth, "title,finished_on\nJaws,not-a-date\n")
    assert auth.get("/api/books").json()["items"][0]["date_finished"] is None


def test_import_reads_dates_and_progress(auth):
    upload(auth, "title,page_count,current_page,date_finished\nJaws,311,311,2026-02-14\n")
    book = auth.get("/api/books").json()["items"][0]
    assert book["date_finished"] == "2026-02-14"
    assert book["progress_percent"] == 100


def test_import_needs_a_title_column(auth):
    response = upload(auth, "name,author\nJaws,Benchley\n")
    assert response.status_code == 400
    assert "title" in response.json()["detail"].lower()


def test_import_tolerates_a_byte_order_mark(auth):
    """Numbers and Excel on macOS both like to add one."""
    response = upload(auth, "\ufefftitle,author\nJaws,Benchley\n")
    assert response.json()["created"] == 1


def test_export_then_import_round_trips(auth, tags):
    make_book(
        auth,
        title="Jaws",
        authors="Peter Benchley",
        page_count=311,
        rating=5,
        tag_ids=[tags["finished"]["id"]],
    )
    exported = auth.get("/api/export/csv").text

    for book in auth.get("/api/books").json()["items"]:
        auth.delete(f"/api/books/{book['id']}")

    upload(auth, exported)
    restored = auth.get("/api/books").json()["items"][0]
    assert restored["title"] == "Jaws"
    assert restored["rating"] == 5
    assert [t["name"] for t in restored["tags"]] == ["Read"]


def test_transfer_needs_a_session(anon):
    assert anon.get("/api/export/csv").status_code == 401
    assert anon.get("/api/export/json").status_code == 401

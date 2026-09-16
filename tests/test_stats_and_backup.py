"""Statistics, yearly goals, CSV round-trips and preferences."""

import io
from datetime import date

from conftest import make_book

THIS_YEAR = date.today().year


# ------------------------------------------------------------------- stats


def test_stats_on_an_empty_library(auth):
    body = auth.get("/api/stats").json()
    assert body["total_books"] == 0
    assert body["average_rating"] is None
    assert body["goal"] is None
    assert len(body["monthly"]) == 12


def test_stats_count_what_is_finished(auth, tags):
    auth.post(
        "/api/books",
        json={
            "title": "Done",
            "page_count": 300,
            "date_finished": f"{THIS_YEAR}-03-14",
            "tag_ids": [tags["finished"]["id"]],
        },
    )
    auth.post("/api/books", json={"title": "Underway", "tag_ids": [tags["reading"]["id"]]})
    make_book(auth, "Untouched")

    body = auth.get("/api/stats").json()
    assert body["total_books"] == 3
    assert body["finished_all_time"] == 1
    assert body["currently_reading"] == 1
    assert body["pages_all_time"] == 300
    assert body["finished_this_year"] == 1
    assert body["pages_this_year"] == 300

    march = next(m for m in body["monthly"] if m["month"] == 3)
    assert march["count"] == 1
    assert march["pages"] == 300


def test_a_previous_year_does_not_count_toward_this_one(auth, tags):
    auth.post(
        "/api/books",
        json={
            "title": "Old",
            "date_finished": "2018-06-01",
            "tag_ids": [tags["finished"]["id"]],
        },
    )
    body = auth.get("/api/stats").json()
    assert body["finished_all_time"] == 1
    assert body["finished_this_year"] == 0

    older = auth.get("/api/stats?year=2018").json()
    assert older["finished_this_year"] == 1


def test_average_rating_ignores_unrated_books(auth):
    make_book(auth, "A", rating=5)
    make_book(auth, "B", rating=4)
    make_book(auth, "C")

    body = auth.get("/api/stats").json()
    assert body["average_rating"] == 4.5
    assert body["rated_count"] == 2


def test_longest_book(auth):
    make_book(auth, "Short", page_count=90)
    make_book(auth, "Doorstop", page_count=1200)
    assert auth.get("/api/stats").json()["longest_book"] == "Doorstop"


def test_tag_breakdown(auth, tags):
    for title in ("A", "B"):
        auth.post("/api/books", json={"title": title, "tag_ids": [tags["owned"]["id"]]})

    by_tag = {t["name"]: t["count"] for t in auth.get("/api/stats").json()["by_tag"]}
    assert by_tag["Owned"] == 2
    assert by_tag["Read"] == 0


# ------------------------------------------------------------------- goals


def test_no_goal_by_default(auth):
    assert auth.get(f"/api/goals/{THIS_YEAR}").json() is None


def test_set_and_track_a_goal(auth, tags):
    created = auth.put(
        "/api/goals",
        json={"year": THIS_YEAR, "target_books": 4, "target_pages": 1000},
    )
    assert created.status_code == 200

    for i in range(2):
        auth.post(
            "/api/books",
            json={
                "title": f"Read {i}",
                "page_count": 250,
                "date_finished": f"{THIS_YEAR}-02-0{i + 1}",
                "tag_ids": [tags["finished"]["id"]],
            },
        )

    goal = auth.get(f"/api/goals/{THIS_YEAR}").json()
    assert goal["books_finished"] == 2
    assert goal["books_percent"] == 50.0
    assert goal["pages_read"] == 500
    assert goal["pages_percent"] == 50.0


def test_setting_a_goal_twice_updates_it(auth):
    auth.put("/api/goals", json={"year": THIS_YEAR, "target_books": 10})
    auth.put("/api/goals", json={"year": THIS_YEAR, "target_books": 25})
    assert auth.get(f"/api/goals/{THIS_YEAR}").json()["target_books"] == 25


def test_a_zero_target_does_not_divide_by_zero(auth):
    auth.put("/api/goals", json={"year": THIS_YEAR, "target_books": 0})
    assert auth.get(f"/api/goals/{THIS_YEAR}").json()["books_percent"] == 0.0


# ---------------------------------------------------------------- transfer


def test_csv_export_has_a_header_and_a_row(auth, tags):
    auth.post(
        "/api/books",
        json={
            "title": "Exported",
            "authors": "A. Writer",
            "rating": 4.0,
            "tag_ids": [tags["owned"]["id"]],
        },
    )
    response = auth.get("/api/export/csv")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]

    text = response.text
    assert text.splitlines()[0].startswith("title,subtitle,authors")
    assert "Exported" in text
    assert "Owned" in text


def test_json_backup_holds_the_whole_library(auth):
    make_book(auth, "Kept")
    body = auth.get("/api/export/json").json()

    assert body["version"] == 1
    assert len(body["books"]) == 1
    assert body["books"][0]["title"] == "Kept"
    assert len(body["categories"]) == 4
    assert "theme.accent" in body["preferences"]


def upload(auth, text, name="import.csv"):
    return auth.post(
        "/api/import/csv",
        files={"file": (name, io.BytesIO(text.encode("utf-8")), "text/csv")},
    )


def test_import_a_simple_csv(auth):
    csv_text = (
        "title,authors,published_year,page_count,rating,tags\n"
        "Dune,Frank Herbert,1965,412,5,Owned; Science fiction\n"
        "Neuromancer,William Gibson,1984,271,4,Owned\n"
    )
    report = upload(auth, csv_text).json()
    assert report["created"] == 2
    assert report["skipped"] == 0

    books = auth.get("/api/books?sort=title").json()
    assert [b["title"] for b in books["items"]] == ["Dune", "Neuromancer"]

    dune = books["items"][0]
    assert dune["page_count"] == 412
    assert dune["rating"] == 5.0
    assert {t["name"] for t in dune["tags"]} == {"Owned", "Science fiction"}


def test_import_puts_unknown_tags_in_their_own_category(auth):
    upload(auth, "title,tags\nDune,Space opera\n")
    categories = {c["name"] for c in auth.get("/api/categories").json()}
    assert "Imported" in categories


def test_import_recognises_goodreads_column_names(auth):
    csv_text = (
        "Title,Author,My Rating,Number of Pages,Date Read,Bookshelves\n"
        "Dune,Frank Herbert,5,412,2021/07/14,sci-fi\n"
    )
    assert upload(auth, csv_text).json()["created"] == 1

    book = auth.get("/api/books").json()["items"][0]
    assert book["authors"] == "Frank Herbert"
    assert book["page_count"] == 412
    assert book["date_finished"] == "2021-07-14"


def test_import_skips_books_already_on_the_shelves(auth):
    csv_text = "title,authors\nDune,Frank Herbert\n"
    assert upload(auth, csv_text).json()["created"] == 1

    second = upload(auth, csv_text).json()
    assert second["created"] == 0
    assert second["skipped"] == 1


def test_import_skips_rows_with_no_title(auth):
    report = upload(auth, "title,authors\n,Nobody\nReal,Someone\n").json()
    assert report["created"] == 1
    assert report["skipped"] == 1


def test_import_survives_an_unrated_zero(auth):
    upload(auth, "title,rating\nUnrated,0\n")
    assert auth.get("/api/books").json()["items"][0]["rating"] is None


def test_a_csv_round_trip_keeps_the_books(auth, tags):
    auth.post(
        "/api/books",
        json={
            "title": "Round Trip",
            "authors": "A. Writer",
            "page_count": 222,
            "tag_ids": [tags["owned"]["id"]],
        },
    )
    exported = auth.get("/api/export/csv").text

    auth.delete(f"/api/books/{auth.get('/api/books').json()['items'][0]['id']}")
    assert auth.get("/api/books").json()["total"] == 0

    assert upload(auth, exported).json()["created"] == 1
    restored = auth.get("/api/books").json()["items"][0]
    assert restored["title"] == "Round Trip"
    assert restored["page_count"] == 222
    assert {t["name"] for t in restored["tags"]} == {"Owned"}


def test_a_headerless_file_is_refused(auth):
    assert upload(auth, "").status_code == 400


# ------------------------------------------------------------- preferences


def test_preferences_are_seeded(auth):
    prefs = auth.get("/api/preferences").json()
    assert prefs["theme.accent"] == "#8a6fe8"
    assert prefs["splash.enabled"] == "true"


def test_a_preference_can_be_written_and_read_back(auth):
    auth.put("/api/preferences/theme.accent", json={"value": "#0e4a5e"})
    assert auth.get("/api/preferences").json()["theme.accent"] == "#0e4a5e"


def test_a_new_preference_key_can_be_created(auth):
    auth.put("/api/preferences/library.density", json={"value": "compact"})
    assert auth.get("/api/preferences").json()["library.density"] == "compact"


def test_transfer_is_behind_the_login(client):
    assert client.get("/api/export/csv").status_code == 401
    assert client.get("/api/preferences").status_code == 401

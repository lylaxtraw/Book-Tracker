from datetime import date

from .conftest import make_book


def test_an_empty_library_reports_zeroes(auth):
    stats = auth.get("/api/stats").json()
    assert stats["total_books"] == 0
    assert stats["finished_books"] == 0
    assert stats["pages_read"] == 0
    assert stats["average_rating"] is None
    assert stats["per_year"] == []


def test_counts_finished_books(auth):
    make_book(auth, title="A", pages=100, finished_on="2025-02-01")
    make_book(auth, title="B", pages=200, finished_on="2026-05-01")
    make_book(auth, title="C", pages=300)

    stats = auth.get("/api/stats").json()
    assert stats["total_books"] == 3
    assert stats["finished_books"] == 2


def test_pages_read_counts_finished_books_plus_progress(auth):
    make_book(auth, title="Done", pages=100, finished_on="2026-01-01")
    make_book(auth, title="Halfway", pages=200, progress_pages=80)
    assert auth.get("/api/stats").json()["pages_read"] == 180


def test_books_are_grouped_by_the_year_they_were_finished(auth):
    make_book(auth, title="A", pages=100, finished_on="2025-02-01")
    make_book(auth, title="B", pages=150, finished_on="2025-11-01")
    make_book(auth, title="C", pages=200, finished_on="2026-05-01")

    per_year = {row["year"]: row for row in auth.get("/api/stats").json()["per_year"]}
    assert per_year[2025]["books"] == 2
    assert per_year[2025]["pages"] == 250
    assert per_year[2026]["books"] == 1


def test_per_year_is_newest_first(auth):
    make_book(auth, title="A", finished_on="2024-01-01")
    make_book(auth, title="B", finished_on="2026-01-01")
    years = [row["year"] for row in auth.get("/api/stats").json()["per_year"]]
    assert years == sorted(years, reverse=True)


def test_average_rating_ignores_unrated_books(auth):
    make_book(auth, title="A", rating=5)
    make_book(auth, title="B", rating=4)
    make_book(auth, title="C")
    assert auth.get("/api/stats").json()["average_rating"] == 4.5


def test_reading_now_counts_the_reading_tag(auth, tags):
    make_book(auth, title="A", tag_ids=[tags["Reading"]["id"]])
    make_book(auth, title="B", tag_ids=[tags["Owned"]["id"]])
    assert auth.get("/api/stats").json()["reading_now"] == 1


def test_per_tag_counts_every_tag(auth, tags):
    make_book(auth, title="A", tag_ids=[tags["Owned"]["id"]])
    make_book(auth, title="B", tag_ids=[tags["Owned"]["id"]])

    counts = {row["tag"]["name"]: row["books"]
              for row in auth.get("/api/stats").json()["per_tag"]}
    assert counts["Owned"] == 2
    assert counts["Wishlist"] == 0


def test_setting_and_updating_a_goal(auth):
    year = date.today().year
    created = auth.put("/api/goals", json={"year": year, "target_books": 24})
    assert created.json()["target_books"] == 24

    updated = auth.put("/api/goals", json={"year": year, "target_books": 30})
    assert updated.json()["target_books"] == 30
    assert len(auth.get("/api/goals").json()) == 1


def test_goal_progress_only_counts_this_year(auth):
    year = date.today().year
    auth.put("/api/goals", json={"year": year, "target_books": 10})
    make_book(auth, title="This year", finished_on=f"{year}-01-15")
    make_book(auth, title="Last year", finished_on=f"{year - 1}-06-01")

    stats = auth.get("/api/stats").json()
    assert stats["goal"]["target_books"] == 10
    assert stats["goal_completed"] == 1


def test_no_goal_set_is_not_an_error(auth):
    stats = auth.get("/api/stats").json()
    assert stats["goal"] is None
    assert stats["goal_completed"] == 0


def test_stats_can_be_asked_about_another_year(auth):
    auth.put("/api/goals", json={"year": 2025, "target_books": 12})
    make_book(auth, title="Old", finished_on="2025-04-01")

    stats = auth.get("/api/stats", params={"year": 2025}).json()
    assert stats["goal"]["year"] == 2025
    assert stats["goal_completed"] == 1

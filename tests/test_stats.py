from datetime import UTC, datetime

from .conftest import make_book


def test_an_empty_library_reports_zeroes(auth):
    stats = auth.get("/api/stats").json()
    assert stats["total_books"] == 0
    assert stats["finished_all_time"] == 0
    assert stats["currently_reading"] == 0
    assert stats["pages_all_time"] == 0
    assert stats["average_rating"] is None
    assert len(stats["monthly"]) == 12


def test_counts_finished_books(auth):
    make_book(auth, title="A", page_count=100, date_finished="2025-02-01")
    make_book(auth, title="B", page_count=200, date_finished="2026-05-01")
    make_book(auth, title="C", page_count=300)

    stats = auth.get("/api/stats").json()
    assert stats["total_books"] == 3
    assert stats["finished_all_time"] == 2


def test_pages_all_time_counts_finished_books_only(auth):
    make_book(auth, title="Done", page_count=100, date_finished="2026-01-01")
    make_book(auth, title="Halfway", page_count=200, current_page=80)
    assert auth.get("/api/stats").json()["pages_all_time"] == 100


def test_stats_can_be_asked_about_a_specific_year(auth):
    make_book(auth, title="A", page_count=100, date_finished="2025-02-01")
    make_book(auth, title="B", page_count=150, date_finished="2025-11-01")
    make_book(auth, title="C", page_count=200, date_finished="2026-05-01")

    stats_2025 = auth.get("/api/stats", params={"year": 2025}).json()
    stats_2026 = auth.get("/api/stats", params={"year": 2026}).json()
    assert stats_2025["finished_this_year"] == 2
    assert stats_2025["pages_this_year"] == 250
    assert stats_2026["finished_this_year"] == 1


def test_monthly_buckets_stay_in_calendar_order(auth):
    months = [row["month"] for row in auth.get("/api/stats").json()["monthly"]]
    assert months == list(range(1, 13))


def test_average_rating_ignores_unrated_books(auth):
    make_book(auth, title="A", rating=5)
    make_book(auth, title="B", rating=4)
    make_book(auth, title="C")
    assert auth.get("/api/stats").json()["average_rating"] == 4.5


def test_reading_now_counts_the_reading_tag(auth, tags):
    make_book(auth, title="A", tag_ids=[tags["reading"]["id"]])
    make_book(auth, title="B", tag_ids=[tags["owned"]["id"]])
    assert auth.get("/api/stats").json()["currently_reading"] == 1


def test_per_tag_counts_every_tag(auth, tags):
    make_book(auth, title="A", tag_ids=[tags["owned"]["id"]])
    make_book(auth, title="B", tag_ids=[tags["owned"]["id"]])

    counts = {row["name"]: row["count"] for row in auth.get("/api/stats").json()["by_tag"]}
    assert counts["Owned"] == 2
    assert counts["Want to Read"] == 0


def test_setting_and_updating_a_goal(auth):
    year = datetime.now(UTC).year
    created = auth.put("/api/goals", json={"year": year, "target_books": 24})
    assert created.json()["target_books"] == 24

    updated = auth.put("/api/goals", json={"year": year, "target_books": 30})
    assert updated.json()["target_books"] == 30
    assert auth.get(f"/api/goals/{year}").json()["target_books"] == 30


def test_goal_progress_only_counts_this_year(auth):
    year = datetime.now(UTC).year
    auth.put("/api/goals", json={"year": year, "target_books": 10})
    make_book(auth, title="This year", date_finished=f"{year}-01-15")
    make_book(auth, title="Last year", date_finished=f"{year - 1}-06-01")

    stats = auth.get("/api/stats").json()
    assert stats["goal"]["target_books"] == 10
    assert stats["goal"]["books_finished"] == 1


def test_no_goal_set_is_not_an_error(auth):
    stats = auth.get("/api/stats").json()
    assert stats["goal"] is None


def test_stats_can_be_asked_about_another_year(auth):
    auth.put("/api/goals", json={"year": 2025, "target_books": 12})
    make_book(auth, title="Old", date_finished="2025-04-01")

    stats = auth.get("/api/stats", params={"year": 2025}).json()
    assert stats["goal"]["year"] == 2025
    assert stats["goal"]["books_finished"] == 1

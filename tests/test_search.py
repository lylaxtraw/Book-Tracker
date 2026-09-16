"""Open Library lookups. Every request is mocked -- these tests never hit the
network, so they pass on a plane and do not depend on a third party being up.
"""

import httpx
import pytest
import respx

from app.openlibrary import (
    build_params,
    parse_doc,
    score_candidate,
    similarity,
)
from app.schemas import AdvancedSearchQuery

SEARCH_URL = "https://openlibrary.org/search.json"


def fake_payload(docs, num_found=None):
    return {"numFound": num_found if num_found is not None else len(docs), "docs": docs}


DOC_MOBY = {
    "key": "/works/OL102749W",
    "title": "Moby-Dick",
    "subtitle": "or, The Whale",
    "author_name": ["Herman Melville"],
    "first_publish_year": 1851,
    "publisher": ["Harper & Brothers"],
    "number_of_pages_median": 635,
    "isbn": ["0142437247", "9780142437247"],
    "language": ["eng"],
    "cover_i": 12345,
    "edition_count": 900,
}

DOC_OTHER = {
    "key": "/works/OL999W",
    "title": "Cooking with Whale Oil",
    "author_name": ["A. Nobody"],
    "first_publish_year": 1902,
    "edition_count": 1,
}


# ---------------------------------------------------------------- unit level


def test_similarity_ignores_case_articles_and_punctuation():
    assert similarity("The Great Gatsby", "great gatsby") > 0.95
    assert similarity("Moby-Dick", "Moby Dick!") > 0.95
    assert similarity("Dune", "Neuromancer") < 0.4


def test_parse_doc_normalises_a_hit():
    candidate = parse_doc(DOC_MOBY)
    assert candidate.title == "Moby-Dick"
    assert candidate.authors == "Herman Melville"
    assert candidate.published_year == 1851
    assert candidate.page_count == 635
    assert candidate.isbn10 == "0142437247"
    assert candidate.isbn13 == "9780142437247"
    assert candidate.cover_url.endswith("/b/id/12345-M.jpg")


def test_parse_doc_survives_a_sparse_hit():
    candidate = parse_doc({"title": "Bare"})
    assert candidate.title == "Bare"
    assert candidate.authors is None
    assert candidate.cover_url is None


def test_parse_doc_handles_a_missing_title():
    assert parse_doc({}).title == "Untitled"


def test_build_params_sends_each_field_separately():
    params = build_params(
        AdvancedSearchQuery(title="Dune", author="Herbert", subject="science fiction")
    )
    assert params["title"] == "Dune"
    assert params["author"] == "Herbert"
    assert params["subject"] == "science fiction"


def test_build_params_turns_years_into_a_range():
    params = build_params(AdvancedSearchQuery(q="whales", year_from=1800, year_to=1900))
    assert "first_publish_year:[1800 TO 1900]" in params["q"]


def test_build_params_leaves_an_open_ended_range_open():
    params = build_params(AdvancedSearchQuery(q="whales", year_from=1990))
    assert "first_publish_year:[1990 TO *]" in params["q"]


def test_build_params_strips_isbn_punctuation():
    params = build_params(AdvancedSearchQuery(isbn="978-0-14-243724-7"))
    assert params["isbn"] == "9780142437247"


def test_scoring_prefers_the_real_match():
    query = AdvancedSearchQuery(title="Moby Dick", author="Melville")
    good = score_candidate(parse_doc(DOC_MOBY), query)
    bad = score_candidate(parse_doc(DOC_OTHER), query)
    assert good > bad
    assert good > 0.7


def test_an_exact_isbn_scores_perfectly():
    query = AdvancedSearchQuery(isbn="978-0-14-243724-7")
    assert score_candidate(parse_doc(DOC_MOBY), query) == 1.0


def test_an_empty_query_is_recognised():
    assert AdvancedSearchQuery().is_empty()
    assert not AdvancedSearchQuery(title="Dune").is_empty()


# ----------------------------------------------------------------- endpoints


@respx.mock
def test_quick_search_ranks_the_best_match_first(auth):
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=fake_payload([DOC_OTHER, DOC_MOBY], 2))
    )
    body = auth.get("/api/search/quick?q=Moby+Dick").json()

    assert body["total_found"] == 2
    assert body["best_match"]["title"] == "Moby-Dick"
    assert body["candidates"][0]["title"] == "Moby-Dick"
    assert body["degraded"] is False


@respx.mock
def test_search_with_no_hits_says_so(auth):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json=fake_payload([])))
    body = auth.get("/api/search/quick?q=asdfghjkl").json()

    assert body["candidates"] == []
    assert "by hand" in body["message"]


@respx.mock
def test_a_weak_best_match_is_flagged(auth):
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=fake_payload([DOC_OTHER]))
    )
    body = auth.get("/api/search/quick?q=The+Fellowship+of+the+Ring").json()
    assert "check before you confirm" in body["message"]


@respx.mock
def test_a_network_failure_degrades_instead_of_erroring(auth):
    respx.get(SEARCH_URL).mock(side_effect=httpx.ConnectError("no route"))
    response = auth.get("/api/search/quick?q=anything")

    assert response.status_code == 200
    body = response.json()
    assert body["degraded"] is True
    assert body["candidates"] == []


@respx.mock
def test_a_server_error_degrades_too(auth):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(503))
    assert auth.get("/api/search/quick?q=anything").json()["degraded"] is True


@respx.mock
def test_advanced_search_posts_every_field(auth):
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json=fake_payload([DOC_MOBY]))
    )
    response = auth.post(
        "/api/search/advanced",
        json={"title": "Moby Dick", "author": "Melville", "year_from": 1800},
    )
    assert response.status_code == 200

    sent = route.calls[0].request.url
    assert "title=Moby+Dick" in str(sent) or "title=Moby%20Dick" in str(sent)


def test_advanced_search_needs_at_least_one_field(auth):
    assert auth.post("/api/search/advanced", json={}).status_code == 400


def test_search_is_behind_the_login(client):
    assert client.get("/api/search/quick?q=dune").status_code == 401


def test_confirming_a_candidate_shelves_it(auth, tags):
    candidate = parse_doc(DOC_MOBY).model_dump()
    response = auth.post(
        f"/api/search/confirm?tag_ids={tags['wishlist']['id']}", json=candidate
    )
    assert response.status_code == 201

    book = response.json()
    assert book["title"] == "Moby-Dick"
    assert book["source"] == "openlibrary"
    assert book["openlibrary_key"] == "/works/OL102749W"
    assert book["page_count"] == 635
    assert [t["role"] for t in book["tags"]] == ["wishlist"]


def test_confirming_the_same_book_twice_is_refused(auth):
    candidate = parse_doc(DOC_MOBY).model_dump()
    assert auth.post("/api/search/confirm", json=candidate).status_code == 201

    second = auth.post("/api/search/confirm", json=candidate)
    assert second.status_code == 409
    assert "already in your library" in second.json()["detail"]


def test_a_manual_book_is_never_treated_as_a_duplicate(auth):
    candidate = parse_doc({"title": "Handwritten"}).model_dump()
    assert auth.post("/api/search/confirm", json=candidate).status_code == 201
    # No Open Library key, so nothing to collide on.
    assert auth.post("/api/search/confirm", json=candidate).status_code == 201


@pytest.mark.parametrize("limit", [0, 51, -3])
def test_the_result_limit_is_bounded(auth, limit):
    assert auth.get(f"/api/search/quick?q=dune&limit={limit}").status_code == 422

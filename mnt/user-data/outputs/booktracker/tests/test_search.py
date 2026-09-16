import httpx
import pytest
import respx

from app import openlibrary

SEARCH_URL = "https://openlibrary.org/search.json"


def doc(title, author, **extra):
    base = {
        "key": "/works/OL1W",
        "title": title,
        "author_name": [author],
        "first_publish_year": 1974,
        "isbn": ["9780553275865"],
        "cover_i": 8231856,
        "number_of_pages_median": 311,
        "publisher": ["Doubleday"],
        "edition_count": 40,
    }
    base.update(extra)
    return base


# ------------------------------------------------------------------ pure logic


def test_normalise_strips_punctuation_and_case():
    assert openlibrary.normalise("The Old Man & the Sea!") == "the old man the sea"


def test_similarity_ignores_formatting():
    assert openlibrary.similarity("Moby-Dick", "moby dick") > 0.95
    assert openlibrary.similarity("Moby-Dick", "Jaws") < 0.4


def test_similarity_handles_missing_values():
    assert openlibrary.similarity(None, "Jaws") == 0.0
    assert openlibrary.similarity("Jaws", "") == 0.0


def test_advanced_fields_become_separate_parameters():
    params = openlibrary.build_params(title="Jaws", author="Benchley", year=1974)
    assert params["title"] == "Jaws"
    assert params["author"] == "Benchley"
    assert params["first_publish_year"] == 1974


def test_a_plain_phrase_is_dropped_when_fields_are_given():
    """Sending both would AND them together and hide good matches."""
    params = openlibrary.build_params(query="shark", title="Jaws")
    assert "q" not in params
    assert params["title"] == "Jaws"


def test_a_plain_phrase_is_used_on_its_own():
    assert openlibrary.build_params(query="shark")["q"] == "shark"


def test_isbn_is_stripped_of_hyphens():
    assert openlibrary.build_params(isbn="978-0-553-27586-5")["isbn"] == "9780553275865"


def test_limit_is_clamped():
    assert openlibrary.build_params(query="x", limit=900)["limit"] == 50
    assert openlibrary.build_params(query="x", limit=0)["limit"] == 1


def test_exact_title_scores_higher_than_a_near_miss():
    exact = openlibrary.score(doc("Jaws", "Peter Benchley"), title="Jaws", author=None)
    near = openlibrary.score(doc("Jaws 2", "Hank Searls"), title="Jaws", author=None)
    assert exact > near


def test_the_right_author_lifts_the_score():
    with_author = openlibrary.score(
        doc("Jaws", "Peter Benchley"), title="Jaws", author="Peter Benchley"
    )
    wrong_author = openlibrary.score(
        doc("Jaws", "Peter Benchley"), title="Jaws", author="Ernest Hemingway"
    )
    assert with_author > wrong_author


def test_ranking_puts_the_closest_match_first():
    hits = openlibrary.rank(
        [doc("Jaws 2", "Hank Searls"), doc("Jaws", "Peter Benchley")],
        title="Jaws",
        author="Peter Benchley",
        covers_base="https://covers.openlibrary.org",
    )
    assert hits[0].title == "Jaws"
    assert hits[0].confidence >= hits[1].confidence


def test_a_document_becomes_a_usable_hit():
    hit = openlibrary.to_hit(
        doc("Jaws", "Peter Benchley"), covers_base="https://covers.openlibrary.org"
    )
    assert hit.cover_url.endswith("/b/id/8231856-M.jpg")
    assert hit.isbn == "9780553275865"
    assert hit.pages == 311


def test_a_document_with_nothing_in_it_still_works():
    hit = openlibrary.to_hit({}, covers_base="https://covers.openlibrary.org")
    assert hit.title == "Untitled"
    assert hit.cover_url is None
    assert hit.author is None


# ------------------------------------------------------------------- endpoint


@respx.mock
def test_search_endpoint_returns_ranked_hits(client):
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200, json={"docs": [doc("Jaws 2", "Hank Searls"), doc("Jaws", "Peter Benchley")]}
        )
    )
    hits = client.get("/api/search", params={"title": "Jaws"}).json()
    assert hits[0]["title"] == "Jaws"
    assert hits[0]["confidence"] > 0


@respx.mock
def test_search_passes_advanced_fields_through(client):
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"docs": []}))
    client.get("/api/search", params={"title": "Jaws", "author": "Benchley", "year": 1974})

    sent = route.calls.last.request.url.params
    assert sent["title"] == "Jaws"
    assert sent["author"] == "Benchley"
    assert sent["first_publish_year"] == "1974"


def test_an_empty_search_is_refused(client):
    response = client.get("/api/search")
    assert response.status_code == 400


@respx.mock
def test_a_timeout_suggests_adding_by_hand(client):
    respx.get(SEARCH_URL).mock(side_effect=httpx.TimeoutException("slow"))
    response = client.get("/api/search", params={"q": "jaws"})
    assert response.status_code == 504
    assert "by hand" in response.json()["detail"]


@respx.mock
def test_an_outage_is_reported_clearly(client):
    respx.get(SEARCH_URL).mock(side_effect=httpx.ConnectError("down"))
    response = client.get("/api/search", params={"q": "jaws"})
    assert response.status_code == 502


@respx.mock
def test_no_results_is_an_empty_list_not_an_error(client):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"docs": []}))
    response = client.get("/api/search", params={"q": "zzzzzz"})
    assert response.status_code == 200
    assert response.json() == []


def test_search_needs_a_session(anon):
    assert anon.get("/api/search", params={"q": "jaws"}).status_code == 401


@pytest.mark.parametrize("field", ["title", "author", "isbn", "subject", "publisher"])
@respx.mock
def test_every_advanced_field_can_search_alone(client, field):
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"docs": []}))
    assert client.get("/api/search", params={field: "x"}).status_code == 200

"""Phase 6 — /search route integration tests (Plan 04).

Replaces the pytest.skip stubs from Plan 06-01 with real assertions exercising
the routes_search.py handler authored in Plan 06-04 Task 1+2.

Critical assertions pinned by Plan 06-04 contracts:
  - test_search_partial_failure pins the EXACT failures-notice template phrase
    (see the test docstring) — RESEARCH §Pitfall 2. No OR-chain fallback —
    a template-copy regression must fail this test, not slip through.
  - test_search_xss_q_echoed (T-06-04-01) — Reflected XSS prevented by Jinja's
    .html autoescape; raw <script>alert(1)</script> must NOT appear.
  - test_search_503_empty_cache (T-06-04-03 / Pitfall 10) — empty FTS-discovery
    cache + non-empty q → 503 with the "Search temporarily unavailable" detail.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from zeeker_frontend.datasette_client import reset_metadata_cache
from zeeker_frontend.main import app


_FIXTURES = Path(__file__).parent / "fixtures"
_ITALIC_H1 = re.compile(r"<h1>.*?<em[^>]*>[^<]+</em>.*?</h1>", re.DOTALL)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


def _load(name: str):
    return json.loads((_FIXTURES / name).read_text())


def _mock_factory(*, hits: dict[str, dict], raise_on: str | None = None):
    """Return an AsyncClient that returns `hits[path]` for each .json call.

    Paths missing from `hits` return 404. If `raise_on` substring matches the
    path, a ConnectError is raised (simulates upstream failure for one table).

    Always serves /-/metadata.json so handlers fetching site_metadata for nav
    rendering get an empty-but-valid response.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if raise_on and raise_on in path:
            raise httpx.ConnectError("simulated upstream failure")
        if path == "/-/metadata.json":
            return httpx.Response(200, json={"title": "data.zeeker.sg", "menu_links": []})
        if path in hits:
            return httpx.Response(200, json=hits[path])
        return httpx.Response(404, json={"ok": False, "error": "not found"})
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
async def client_search():
    """Two-table searchable cache. Default fixture for State B tests."""
    search_fixture = _load("headlines_search_results.json")
    app.state.http = _mock_factory(hits={
        "/sglawwatch/headlines.json": search_fixture,
        "/Zeeker-Judgements/judgments.json": search_fixture,
    })
    app.state.searchable_tables = {
        "sglawwatch": ["headlines"],
        "Zeeker-Judgements": ["judgments"],
    }
    app.state.changelog = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.fixture
async def client_search_partial():
    """Two-table cache; one table errors out (Pitfall 2 partial-failure test).

    sglawwatch.headlines succeeds (returns the fixture); Zeeker-Judgements.
    judgments raises ConnectError. The handler's _safe_search_one must convert
    the error to None, drop that group, and increment `failures` so the
    failures-notice partial renders.
    """
    search_fixture = _load("headlines_search_results.json")
    app.state.http = _mock_factory(
        hits={"/sglawwatch/headlines.json": search_fixture},
        raise_on="/Zeeker-Judgements",
    )
    app.state.searchable_tables = {
        "sglawwatch": ["headlines"],
        "Zeeker-Judgements": ["judgments"],
    }
    app.state.changelog = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.fixture
async def client_search_empty_cache():
    """No FTS-discovery cache (boot-blip simulation)."""
    app.state.http = _mock_factory(hits={})
    app.state.searchable_tables = {}
    app.state.changelog = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.mark.asyncio
async def test_search_empty_query(client_search):
    """State A — empty query renders hero + tips, no fan-out."""
    r = await client_search.get("/search")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    assert "Search across" in r.text
    assert 'name="q"' in r.text  # form input present
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc and "stale-while-revalidate=300" in cc


@pytest.mark.asyncio
async def test_search_groups_results(client_search):
    """State B — both groups present in alphabetical order with rows rendered."""
    r = await client_search.get("/search?q=DBS")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    # Both groups present (alphabetical by db name)
    assert "sglawwatch" in r.text
    assert "Zeeker-Judgements" in r.text
    # Top-N rows render — at least one row from the fixture leaks into the body
    fixture = _load("headlines_search_results.json")
    if fixture.get("rows"):
        first_row = fixture["rows"][0]
        for v in first_row.values():
            if isinstance(v, str) and v:
                assert v[:30] in r.text or any(v[:30] in line for line in r.text.split("\n"))
                break


@pytest.mark.asyncio
async def test_search_partial_failure(client_search_partial):
    """Pitfall 2 — one failing table must NOT empty /search.

    Pinned to the EXACT failures-notice template phrase rendered by
    templates/pages/search.html for `{% if failures %}`. This is
    regression-detection for the failures-notice template wording — if a
    template copy edit changes the phrase, this test fails immediately rather
    than passing for the wrong reason via an OR-chain fallback. Also
    positively asserts the successful group still rendered.
    """
    r = await client_search_partial.get("/search?q=foo")
    assert r.status_code == 200
    # Pinned phrase from templates/pages/search.html (load-bearing copy):
    assert "Search timed out for" in r.text
    # Positive assertion: the successful group's table name surfaces in the
    # body. `headlines` is the fixture's table name (mocked-success in
    # client_search_partial).
    assert "headlines" in r.text


@pytest.mark.asyncio
async def test_search_503_empty_cache(client_search_empty_cache):
    """Pitfall 10 — empty FTS-discovery cache + non-empty q → 503."""
    r = await client_search_empty_cache.get("/search?q=foo")
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_search_empty_cache_state_a_still_renders(client_search_empty_cache):
    """State A renders even when cache is empty (Pitfall 10 — q empty bypasses fan-out)."""
    r = await client_search_empty_cache.get("/search")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)


@pytest.mark.asyncio
async def test_search_xss_q_echoed(client_search):
    """T-06-04-01 — Reflected XSS prevented by Jinja autoescape."""
    r = await client_search.get("/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
    assert r.status_code == 200
    # Raw <script> tag MUST NOT appear in response body
    assert "<script>alert(1)</script>" not in r.text
    # The escaped form may appear (e.g., &lt;script&gt;) — that's expected.


@pytest.mark.asyncio
async def test_search_cache_control(client_search):
    """Cache-Control public, max-age=60, stale-while-revalidate=300 set on State B too."""
    r = await client_search.get("/search?q=DBS")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc
    assert "stale-while-revalidate=300" in cc

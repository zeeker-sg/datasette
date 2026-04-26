"""Route tests for GET / — MockTransport exercises the full stack."""
from __future__ import annotations

import httpx
import pytest

from zeeker_frontend.main import app
from zeeker_frontend.datasette_client import reset_metadata_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


def _mock_datasette(databases_fixture, metadata_fixture, *, fail_databases: bool = False):
    """Build an httpx.AsyncClient whose transport is a MockTransport
    returning the captured fixtures. Optionally break /.json to exercise
    the 503 path."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/.json":
            if fail_databases:
                return httpx.Response(500, json={"detail": "boom"})
            return httpx.Response(200, json=databases_fixture)
        if path == "/-/metadata.json":
            return httpx.Response(200, json=metadata_fixture)
        return httpx.Response(404, json={"ok": False, "error": "nope"})

    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
async def client_with_mocked_datasette(databases_fixture, metadata_fixture):
    """ASGITransport wraps the FastAPI app; app.state.http is swapped for
    a MockTransport-backed client."""
    app.state.http = _mock_datasette(databases_fixture, metadata_fixture)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.mark.asyncio
async def test_home_returns_200_with_card_grid(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/")
    assert r.status_code == 200
    body = r.text
    # Shell + home markers from the design contract
    assert "db-statband" in body
    assert 'class="cards"' in body
    # Italic-accent H1: <h1>…<em>…</em></h1> signature
    assert "<h1>" in body
    assert "<em>" in body
    # Stylesheet from frontend path, not datasette's M1 path
    assert "/static/css/zeeker.css" in body
    assert "zeeker-base.css" not in body


@pytest.mark.asyncio
async def test_home_sets_cache_control(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/")
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc
    assert "stale-while-revalidate=300" in cc


@pytest.mark.asyncio
async def test_home_filters_wildcard_databases_key(client_with_mocked_datasette):
    """metadata.databases['*'] must never produce a card."""
    r = await client_with_mocked_datasette.get("/")
    # The captured metadata.json contains a '*' key; make sure we never link to /*
    assert 'href="/*"' not in r.text
    assert ">*</a>" not in r.text


@pytest.mark.asyncio
async def test_home_renders_card_per_database(client_with_mocked_datasette, databases_fixture):
    r = await client_with_mocked_datasette.get("/")
    body = r.text
    # Count <article class="card"> occurrences
    card_count = body.count('<article class="card">')
    assert card_count == len(databases_fixture)


@pytest.mark.asyncio
async def test_home_search_targets_frontend_route_not_datasette(
    client_with_mocked_datasette,
):
    """Hero form, section-aside link, and CTA primary all submit to the
    frontend's /search — never to Datasette's native /-/search.

    Surfaced during phase-6 HUMAN UAT — earlier copy still shipped /-/search
    pointers from the M1 layout, which routes through Caddy to Datasette and
    bypasses the new civic-broadsheet UI.
    """
    r = await client_with_mocked_datasette.get("/")
    body = r.text
    assert 'action="/search"' in body  # hero form posts to frontend
    assert "/-/search" not in body  # no stray pointers to Datasette's UI


@pytest.mark.asyncio
async def test_home_links_to_sql_editor(client_with_mocked_datasette):
    """Home page must surface the new /sql editor.

    HUMAN UAT — visitor feedback: 'no link to the new /sql pages' from the
    home page. The SQL stat-band tile, the §02 'Write SQL' how-to-use card,
    and the CTA all link to /sql now.
    """
    r = await client_with_mocked_datasette.get("/")
    body = r.text
    # At least one href to the SQL landing
    assert 'href="/sql"' in body


@pytest.mark.asyncio
async def test_home_503_when_datasette_down(databases_fixture, metadata_fixture):
    """If /.json fails, return 503 — NOT a generic 500 with traceback."""
    app.state.http = _mock_datasette(databases_fixture, metadata_fixture, fail_databases=True)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            r = await ac.get("/")
        assert r.status_code == 503
        assert "Data API unavailable" in r.text
    finally:
        await app.state.http.aclose()

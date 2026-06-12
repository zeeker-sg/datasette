"""Route tests for GET /{db} — MockTransport exercises the full stack."""
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


def _mock_datasette(sglawwatch_fixture, metadata_fixture):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/sglawwatch.json":
            return httpx.Response(200, json=sglawwatch_fixture)
        if path == "/-/metadata.json":
            return httpx.Response(200, json=metadata_fixture)
        # Unknown database → datasette 404 shape
        return httpx.Response(
            404,
            json={"ok": False, "error": "Database not found", "status": 404, "title": None},
        )

    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
async def client_with_mocked_datasette(sglawwatch_fixture, metadata_fixture):
    app.state.http = _mock_datasette(sglawwatch_fixture, metadata_fixture)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.mark.asyncio
async def test_database_returns_200_with_editorial_list(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/sglawwatch")
    assert r.status_code == 200
    body = r.text
    # Shell markers
    assert "db-header" in body
    assert "db-statband" in body
    # Editorial-row list — both the .list container and a .row
    assert 'class="list"' in body
    # The visible table 'headlines' (NOT hidden in the captured fixture)
    assert "headlines" in body
    # Frontend CSS path
    assert "/static/css/zeeker.css" in body
    assert "zeeker-base.css" not in body


@pytest.mark.asyncio
async def test_database_unknown_returns_404(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/no-such-database")
    assert r.status_code == 404
    # Must be an actual 404, not a 500-traceback
    assert "Internal Server Error" not in r.text


@pytest.mark.asyncio
async def test_database_filters_hidden_zeeker_tables(client_with_mocked_datasette):
    """The captured fixture includes `_zeeker_*` tables with hidden=true.
    The rendered page must NOT contain any of them."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    assert "_zeeker" not in r.text, (
        "Hidden _zeeker_* tables leaked into the rendered page"
    )


@pytest.mark.asyncio
async def test_database_filters_fts_tables(client_with_mocked_datasette):
    """The captured sglawwatch fixture includes `headlines_fts`, `headlines_fts_data`,
    etc., all with hidden=true. The rendered editorial-row list must exclude them.
    This is the load-bearing test for the single-predicate filter."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    # We allow the FTS *badge* text "FTS" on visible tables (.date-col)
    # but no reference to the hidden FTS table itself.
    assert "headlines_fts" not in r.text, (
        "FTS internal table 'headlines_fts' leaked — filter must trust hidden=true"
    )


@pytest.mark.asyncio
async def test_database_filters_fragments_tables(client_with_mocked_datasette):
    """*_fragments chunk tables (full-text content) must not be listed even
    when Datasette reports hidden=false (name predicate)."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    assert 'href="/sglawwatch/about_singapore_law_fragments"' not in r.text
    assert "Fragments" not in r.text


@pytest.mark.asyncio
async def test_database_filters_metadata_and_schema_versions(client_with_mocked_datasette):
    """sglawwatch's `metadata` and `schema_versions` tables are flagged
    hidden via site metadata — they must not appear in the table list."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    assert 'href="/sglawwatch/metadata"' not in r.text
    assert 'href="/sglawwatch/schema_versions"' not in r.text


@pytest.mark.asyncio
async def test_database_filters_views(client_with_mocked_datasette):
    """Views pass through the same hidden predicate as tables."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    body = r.text
    # visible view listed
    assert 'href="/sglawwatch/recent_headlines_view"' in body
    # _zeeker-prefixed and *_fts* views filtered
    assert "_zeeker_audit_view" not in body
    assert "headlines_fts_view" not in body


@pytest.mark.asyncio
async def test_database_filters_canned_queries(client_with_mocked_datasette):
    """Canned queries pass through the same hidden predicate as tables."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    body = r.text
    assert 'href="/sglawwatch/recent_headlines"' in body
    assert "Recent Headlines" in body
    assert "_zeeker_admin_query" not in body


@pytest.mark.asyncio
async def test_database_no_sql_links(client_with_mocked_datasette):
    """The /sql editor is gone — no ?sql= links may render."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    assert "?sql=" not in r.text


@pytest.mark.asyncio
async def test_database_protected_table_json_export_only(client_with_mocked_datasette):
    """headlines carries protected column `text` → no per-table CSV anchor;
    unprotected about_singapore_law keeps both."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    body = r.text
    assert 'href="/sglawwatch/headlines.csv"' not in body
    assert 'href="/sglawwatch/headlines.json"' in body
    assert 'href="/sglawwatch/about_singapore_law.csv"' in body
    assert 'href="/sglawwatch/about_singapore_law.json"' in body


@pytest.mark.asyncio
async def test_database_italic_accent_h1(client_with_mocked_datasette):
    """Last-word-italic H1 split (M1 WARN-04)."""
    import re
    r = await client_with_mocked_datasette.get("/sglawwatch")
    # Match <h1>…<em>…</em>…</h1> even across whitespace/newlines
    pattern = re.compile(r"<h1>.*?<em>[^<]+</em>.*?</h1>", re.DOTALL)
    assert pattern.search(r.text), "italic-accent H1 not found"


@pytest.mark.asyncio
async def test_database_cache_control_header(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/sglawwatch")
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc
    assert "stale-while-revalidate=300" in cc


@pytest.mark.asyncio
async def test_database_renders_breadcrumb(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/sglawwatch")
    # base.html renders <div class="db-crumb"> only when breadcrumbs context is truthy.
    assert 'class="db-crumb"' in r.text

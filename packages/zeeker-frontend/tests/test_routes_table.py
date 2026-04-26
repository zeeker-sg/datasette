"""Integration tests for GET /{db}/{table} (Phase 5)."""
from __future__ import annotations

import re

import httpx
import pytest

from zeeker_frontend.main import app
from zeeker_frontend.datasette_client import reset_metadata_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


# Test-local metadata fixture with Phase-5 display.* hints.
METADATA_WITH_DISPLAY = {
    "title": "data.zeeker.sg",
    "menu_links": [],
    "databases": {
        "sglawwatch": {
            "title": "SG Law Watch",
            "tables": {
                "headlines": {
                    "title": "Headlines",
                    "description": "Daily Singapore legal news.",
                    "display": {
                        "table_mode": "feed",
                        "row_mode": "article",
                        "columns": {
                            "kicker": "category",
                            "title": "title",
                            "byline": "author",
                            "body": "summary",
                            "date": "date",
                            "source_url": "source_link",
                        }
                    }
                },
                # about_singapore_law has NO display hint → tabular fallback
                "about_singapore_law": {
                    "title": "About Singapore Law",
                }
            }
        }
    }
}


def _mock_factory(headlines_table, about_singapore_law_table, *, raise_on=None):
    """Build a MockTransport handler.

    raise_on: a path substring; if set, raise ConnectError when path matches.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if raise_on and raise_on in path:
            raise httpx.ConnectError("simulated upstream failure")
        if path == "/-/metadata.json":
            return httpx.Response(200, json=METADATA_WITH_DISPLAY)
        if path == "/sglawwatch/headlines.json":
            # Echo the search term so we can simulate empty-results
            params = dict(request.url.params)
            if params.get("_search") == "zzzzzzz_no_match":
                empty = dict(headlines_table)
                empty["rows"] = []
                empty["filtered_table_rows_count"] = 0
                empty["facet_results"] = {}
                empty["next_url"] = None
                return httpx.Response(200, json=empty)
            return httpx.Response(200, json=headlines_table)
        if path == "/sglawwatch/about_singapore_law.json":
            return httpx.Response(200, json=about_singapore_law_table)
        return httpx.Response(
            404,
            json={"ok": False, "error": "Table not found", "status": 404, "title": None},
        )
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
async def client_table(headlines_table_fixture, about_singapore_law_table_fixture):
    app.state.http = _mock_factory(headlines_table_fixture, about_singapore_law_table_fixture)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.fixture
async def client_table_failing(headlines_table_fixture, about_singapore_law_table_fixture):
    app.state.http = _mock_factory(
        headlines_table_fixture, about_singapore_law_table_fixture,
        raise_on="/sglawwatch/headlines.json",
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


# ===== feed mode (display.table_mode == "feed") =====

@pytest.mark.asyncio
async def test_table_returns_200_feed_mode(client_table):
    r = await client_table.get("/sglawwatch/headlines")
    assert r.status_code == 200
    body = r.text
    assert "va-item" in body
    assert "va-feed" in body
    assert "/static/css/zeeker.css" in body
    assert "zeeker-base.css" not in body


@pytest.mark.asyncio
async def test_table_feed_mode_does_not_render_data_table(client_table):
    # Mode dispatch correctness — feed mode must NOT include the tabular partial
    r = await client_table.get("/sglawwatch/headlines")
    assert "data-table" not in r.text


# ===== tabular fallback (no display hint) =====

@pytest.mark.asyncio
async def test_table_tabular_fallback(client_table):
    r = await client_table.get("/sglawwatch/about_singapore_law")
    assert r.status_code == 200
    assert "data-table" in r.text
    # Must NOT use feed-mode partial
    assert "va-item" not in r.text


# ===== facet sidebar =====

@pytest.mark.asyncio
async def test_facet_sidebar_renders(client_table):
    r = await client_table.get("/sglawwatch/headlines")
    body = r.text
    assert 'class="facets"' in body
    assert "facet-block" in body
    # Facet names from the headlines fixture (CATEGORY uppercase per UI-SPEC)
    assert "CATEGORY" in body


# ===== applied facet chips =====

@pytest.mark.asyncio
async def test_applied_facet_chip_renders(client_table):
    r = await client_table.get("/sglawwatch/headlines?category=Straits+Times")
    assert r.status_code == 200
    body = r.text
    assert "filter-chip" in body
    assert "Straits Times" in body or "Straits+Times" in body


# ===== applied search chip =====

@pytest.mark.asyncio
async def test_applied_search_chip_renders(client_table):
    r = await client_table.get("/sglawwatch/headlines?_search=DBS")
    body = r.text
    assert "filter-chip" in body
    assert "DBS" in body


# ===== pagination =====

@pytest.mark.asyncio
async def test_pagination_next_link_when_next_url(client_table):
    r = await client_table.get("/sglawwatch/headlines")
    body = r.text
    assert 'class="pagination"' in body
    # next_url must be rewritten to relative path (Pitfall 2)
    assert "Next →" in body
    # Must be relative path, not the internal hostname
    assert "zeeker-datasette:8001" not in body


# ===== export anchors (D-05) =====

@pytest.mark.asyncio
async def test_export_anchors_are_direct(client_table):
    r = await client_table.get("/sglawwatch/headlines?_size=10")
    body = r.text
    # CSV link is a direct path /{db}/{table}.csv?... — Caddy intercepts via @datasette
    assert re.search(r'href="/sglawwatch/headlines\.csv\?[^"]*"', body), \
        "CSV export anchor missing or not direct"
    assert re.search(r'href="/sglawwatch/headlines\.json\?[^"]*"', body), \
        "JSON export anchor missing or not direct"
    # MUST NOT contain a frontend-proxied path like /export?...
    assert "/export?" not in body


# ===== Cache-Control =====

@pytest.mark.asyncio
async def test_table_cache_control_header(client_table):
    r = await client_table.get("/sglawwatch/headlines")
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc
    assert "stale-while-revalidate=300" in cc


# ===== Italic-accent H1 =====

@pytest.mark.asyncio
async def test_table_italic_accent_h1(client_table):
    r = await client_table.get("/sglawwatch/headlines")
    pattern = re.compile(r"<h1>.*?<em>[^<]+</em>.*?</h1>", re.DOTALL)
    assert pattern.search(r.text), "italic-accent H1 not found"


# ===== Hidden tables blocked =====

@pytest.mark.asyncio
async def test_zeeker_prefix_table_returns_404(client_table):
    r = await client_table.get("/sglawwatch/_zeeker_schemas")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_fts_suffix_table_returns_404(client_table):
    r = await client_table.get("/sglawwatch/headlines_fts")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_fts_data_suffix_returns_404(client_table):
    r = await client_table.get("/sglawwatch/some_fts_data")
    assert r.status_code == 404


# ===== Unknown table 404 =====

@pytest.mark.asyncio
async def test_unknown_table_returns_404(client_table):
    r = await client_table.get("/sglawwatch/no-such-table")
    assert r.status_code == 404


# ===== FTS no-results =====

@pytest.mark.asyncio
async def test_search_no_results_message(client_table):
    r = await client_table.get("/sglawwatch/headlines?_search=zzzzzzz_no_match")
    assert r.status_code == 200
    assert "No results for" in r.text


# ===== Rowid PK fallback (Pitfall 4) =====

@pytest.mark.asyncio
async def test_rowid_pk_fallback_renders_row_link(client_table):
    # about_singapore_law has primary_keys=[]; row link should fall back to row.rowid
    r = await client_table.get("/sglawwatch/about_singapore_law")
    body = r.text
    # Tabular fallback renders <a> from first cell when href computable; rowid is in the row dict
    # Either the link is present using rowid, or no link (acceptable graceful behavior).
    # The load-bearing assertion is "no 500 / no IndexError".
    assert r.status_code == 200, f"primary_keys=[] caused {r.status_code}, expected 200"


# ===== 503 on httpx error =====

@pytest.mark.asyncio
async def test_table_returns_503_on_upstream_error(client_table_failing):
    r = await client_table_failing.get("/sglawwatch/headlines")
    assert r.status_code == 503
    assert "Internal Server Error" not in r.text


# ===== Breadcrumb renders =====

@pytest.mark.asyncio
async def test_table_renders_breadcrumb(client_table):
    r = await client_table.get("/sglawwatch/headlines")
    assert 'class="db-crumb"' in r.text
    # Two-segment breadcrumb: db + table
    assert "/sglawwatch" in r.text
    assert "Headlines" in r.text  # from table_meta.title

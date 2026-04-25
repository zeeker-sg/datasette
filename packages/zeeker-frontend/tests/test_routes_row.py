"""Integration tests for GET /{db}/{table}/{pk} (Phase 5, Plan 03)."""
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


METADATA_WITH_DISPLAY = {
    "title": "data.zeeker.sg",
    "menu_links": [],
    "databases": {
        "sglawwatch": {
            "title": "SG Law Watch",
            "tables": {
                "headlines": {
                    "title": "Headlines",
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
                        },
                    },
                },
                "about_singapore_law": {  # NO display.row_mode → tabular fallback
                    "title": "About Singapore Law",
                },
                "longform_articles": {
                    "title": "Longform",
                    "display": {
                        "row_mode": "longform",
                        "columns": {
                            "title": "title",
                            "body": "body",
                            "date": "date",
                            "source_url": "source_url",
                        },
                    },
                },
            },
        },
        "Zeeker-Judgements": {
            "title": "Zeeker Judgements",
            "tables": {
                "judgments": {
                    "title": "Judgments",
                    "display": {
                        "table_mode": "tabular",
                        "row_mode": "judgment",
                        "columns": {
                            "title": "case_name",
                            "kicker": "court",
                            "citation": "citation",
                            "body": "text",
                            "date": "decision_date",
                            "source_url": "source_url",
                        },
                    },
                },
            },
        },
    },
}


# Synthetic fixture — longform table (primary_keys=[] rowid-only)
LONGFORM_ROW_FIXTURE = {
    "database": "sglawwatch",
    "table": "longform_articles",
    "rows": [{
        "rowid": 1,
        "title": "A long-form analysis of administrative law",
        "body": ("Lorem ipsum " * 100).strip(),  # > 200 chars
        "date": "2025-12-01",
        "source_url": "https://example.com/article",
    }],
    "columns": ["rowid", "title", "body", "date", "source_url"],
    "primary_keys": [],
    "primary_key_values": ["1"],
    "units": {},
}


# Synthetic fixture for tabular fallback — row with long-text field
TABULAR_ROW_FIXTURE = {
    "database": "sglawwatch",
    "table": "about_singapore_law",
    "rows": [{
        "rowid": 1,
        "section": "Constitutional Law",
        "title": "On the separation of powers",
        "content": ("This is a very long-form discourse on " * 30).strip(),  # > 200 chars
        "last_scraped": "2025-12-01",
        "item_url": "https://example.com/article",
    }],
    "columns": ["rowid", "section", "title", "content", "last_scraped", "item_url"],
    "primary_keys": [],
    "primary_key_values": ["1"],
    "units": {},
}


def _mock_factory(headlines_row, judgments_row, *, raise_on=None):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if raise_on and raise_on in path:
            raise httpx.ConnectError("simulated upstream failure")
        if path == "/-/metadata.json":
            return httpx.Response(200, json=METADATA_WITH_DISPLAY)
        if path.startswith("/sglawwatch/headlines/") and path.endswith(".json"):
            return httpx.Response(200, json=headlines_row)
        if path.startswith("/Zeeker-Judgements/judgments/") and path.endswith(".json"):
            return httpx.Response(200, json=judgments_row)
        if path.startswith("/sglawwatch/longform_articles/") and path.endswith(".json"):
            return httpx.Response(200, json=LONGFORM_ROW_FIXTURE)
        if path.startswith("/sglawwatch/about_singapore_law/") and path.endswith(".json"):
            return httpx.Response(200, json=TABULAR_ROW_FIXTURE)
        return httpx.Response(
            404,
            json={"ok": False, "error": "Row not found", "status": 404, "title": None},
        )
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
async def client_row(headlines_row_fixture, judgments_row_fixture):
    app.state.http = _mock_factory(headlines_row_fixture, judgments_row_fixture)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.fixture
async def client_row_failing(headlines_row_fixture, judgments_row_fixture):
    app.state.http = _mock_factory(
        headlines_row_fixture, judgments_row_fixture,
        raise_on="/sglawwatch/headlines/",
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


# ===== article mode =====

@pytest.mark.asyncio
async def test_row_returns_200_article_mode(client_row):
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    assert r.status_code == 200
    body = r.text
    assert 'class="article' in body
    assert 'class="aside"' in body
    assert "/static/css/zeeker.css" in body


@pytest.mark.asyncio
async def test_row_article_mode_does_not_render_dateline(client_row):
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    # judgment-only chrome must not appear
    assert 'class="dateline"' not in r.text


# ===== judgment mode =====

@pytest.mark.asyncio
async def test_row_judgment_mode_renders_dateline(client_row):
    r = await client_row.get("/Zeeker-Judgements/judgments/1")
    assert r.status_code == 200
    body = r.text
    assert 'class="dateline"' in body
    # tag-chip from synthetic subject_tags
    assert "tag-chip" in body


# ===== longform mode (no aside) =====

@pytest.mark.asyncio
async def test_row_longform_mode_no_aside(client_row):
    r = await client_row.get("/sglawwatch/longform_articles/1")
    assert r.status_code == 200
    body = r.text
    assert 'class="article' in body  # article variant
    assert 'class="aside"' not in body  # longform has NO sidebar


# ===== tabular fallback (no display.row_mode) =====

@pytest.mark.asyncio
async def test_row_tabular_fallback_renders_dl(client_row):
    r = await client_row.get("/sglawwatch/about_singapore_law/1")
    assert r.status_code == 200
    body = r.text
    assert "<dl" in body  # key-value list


@pytest.mark.asyncio
async def test_row_tabular_long_text_uses_details(client_row):
    # TABULAR_ROW_FIXTURE has 'content' field > 200 chars
    r = await client_row.get("/sglawwatch/about_singapore_law/1")
    body = r.text
    assert "<details" in body
    assert "Show full content" in body


# ===== Cache-Control =====

@pytest.mark.asyncio
async def test_row_cache_control_header(client_row):
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc
    assert "stale-while-revalidate=300" in cc


# ===== Italic-accent H1 =====

@pytest.mark.asyncio
async def test_row_italic_accent_h1(client_row):
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    pattern = re.compile(r"<h1>.*?<em>[^<]+</em>.*?</h1>", re.DOTALL)
    assert pattern.search(r.text), "italic-accent H1 not found"


# ===== 3-segment breadcrumb =====

@pytest.mark.asyncio
async def test_row_renders_three_segment_breadcrumb(client_row):
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    body = r.text
    assert 'class="db-crumb"' in body
    # All three breadcrumb segments must appear
    assert "/sglawwatch" in body
    assert "/sglawwatch/headlines" in body  # link to table page
    # PK should be truncated to 12 chars (first 12 chars of the long PK)
    assert "fdd3ea972982" in body  # first 12 chars of the long PK


# ===== Hidden tables blocked =====

@pytest.mark.asyncio
async def test_row_zeeker_prefix_returns_404(client_row):
    r = await client_row.get("/sglawwatch/_zeeker_schemas/some-pk")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_row_fts_suffix_returns_404(client_row):
    r = await client_row.get("/sglawwatch/headlines_fts/some-pk")
    assert r.status_code == 404


# ===== Unknown row 404 =====

@pytest.mark.asyncio
async def test_unknown_row_returns_404(client_row):
    r = await client_row.get("/sglawwatch/no-such-table/no-such-pk")
    assert r.status_code == 404


# ===== 503 on httpx error =====

@pytest.mark.asyncio
async def test_row_returns_503_on_upstream_error(client_row_failing):
    r = await client_row_failing.get("/sglawwatch/headlines/anything")
    assert r.status_code == 503


# ===== Row export anchor renders =====

@pytest.mark.asyncio
async def test_row_export_json_anchor_present(client_row):
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    body = r.text
    assert re.search(r'href="/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e\.json"', body)


# ===== rowid-only fallback (longform fixture has primary_keys=[]) =====

@pytest.mark.asyncio
async def test_row_rowid_only_table_renders_200(client_row):
    # primary_keys=[] should not crash the handler (Pitfall 4)
    r = await client_row.get("/sglawwatch/longform_articles/1")
    assert r.status_code == 200

"""Integration tests for GET /{db}/{table}/{pk} (Phase 5; catalogue posture).

Uniform catalogue rule: protected (full-text) column values NEVER render on
row pages — no <details> full-content blocks, no full text in the aside.
"""
from __future__ import annotations

import re

import httpx
import pytest

from zeeker_frontend.main import app
from zeeker_frontend.datasette_client import reset_metadata_cache


SENTINEL = "SENTINEL-FULL-TEXT-MUST-NOT-RENDER"
JUDGMENT_SENTINEL = "JUDGMENT-SENTINEL-FULL-TEXT-MUST-NOT-RENDER"


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


_STRIP_COLUMNS = {
    "default_deny_names": ["content_text", "full_text", "html_raw", "footnote_text"],
    "tables": {
        "sglawwatch": {
            "commentaries": ["full_text"],
            "headlines": ["text"],
            "about_singapore_law": ["content"],
            "about_singapore_law_fragments": ["content_text"],
        },
        "zeeker-judgements": {
            "judgments": ["content_text"],
            "judgments_fragments": ["content_text", "html_raw", "footnote_text"],
        },
    },
}


METADATA_WITH_DISPLAY = {
    "title": "data.zeeker.sg",
    "menu_links": [],
    "plugins": {"strip-columns": _STRIP_COLUMNS},
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
                "about_singapore_law": {  # NO display.row_mode → catalogue-record fallback
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
        "zeeker-judgements": {
            "title": "Zeeker Judgements",
            "tables": {
                "judgments": {
                    "title": "Judgments",
                    "display": {
                        "row_mode": "judgment",
                        "columns": {
                            "title": "case_name",
                            "kicker": "court",
                            "citation": "citation",
                            # Deliberately maps body to the PROTECTED column —
                            # the server must drop it and fall back to the
                            # summary-class heuristic (summary/court_summary).
                            "body": "content_text",
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
        "body": ("Lorem ipsum " * 100).strip(),  # > 200 chars, NOT protected
        "date": "2025-12-01",
        "source_url": "https://example.com/article",
    }],
    "columns": ["rowid", "title", "body", "date", "source_url"],
    "primary_keys": [],
    "primary_key_values": ["1"],
    "units": {},
}


# Synthetic fixture for the catalogue-record fallback — row with a PROTECTED
# long-text field (`content` is protected for sglawwatch/about_singapore_law).
TABULAR_ROW_FIXTURE = {
    "database": "sglawwatch",
    "table": "about_singapore_law",
    "rows": [{
        "rowid": 1,
        "section": "Constitutional Law",
        "title": "On the separation of powers",
        "content": (SENTINEL + " This is a very long-form discourse on " * 10).strip(),
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
        if path.startswith("/zeeker-judgements/judgments/") and path.endswith(".json"):
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


@pytest.mark.asyncio
async def test_row_article_aside_never_renders_protected_value(client_row):
    """The headlines `text` column is protected — even though its sample
    value is shorter than 200 chars, it must never appear in the aside."""
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    assert SENTINEL not in r.text


@pytest.mark.asyncio
async def test_row_article_protected_table_has_no_csv_export(client_row):
    r = await client_row.get("/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e")
    body = r.text
    assert ".csv?" not in body, "CSV export anchor must not render for protected table"
    assert re.search(r'href="/sglawwatch/headlines/fdd3ea972982da1e8326e4233586bd8e\.json"', body)


# ===== judgment mode =====

@pytest.mark.asyncio
async def test_row_judgment_mode_renders_dateline(client_row):
    r = await client_row.get("/zeeker-judgements/judgments/1")
    assert r.status_code == 200
    body = r.text
    assert 'class="dateline"' in body
    # tag-chip from synthetic subject_tags
    assert "tag-chip" in body


@pytest.mark.asyncio
async def test_row_judgment_body_is_summary_not_full_text(client_row):
    """display.columns.body points at protected content_text — the server
    must drop the override and fall back to a summary-class column."""
    r = await client_row.get("/zeeker-judgements/judgments/1")
    body = r.text
    assert JUDGMENT_SENTINEL not in body
    # the summary-class fallback renders instead
    assert "upheld the conviction and sentence" in body


@pytest.mark.asyncio
async def test_row_judgment_prominent_source_link(client_row):
    r = await client_row.get("/zeeker-judgements/judgments/1")
    body = r.text
    assert "Read the full judgment at the source" in body
    assert "elitigation.sg/judgments/sgca/2025/12.pdf" in body


@pytest.mark.asyncio
async def test_row_judgment_keeps_citation_court_date_chrome(client_row):
    r = await client_row.get("/zeeker-judgements/judgments/1")
    body = r.text
    assert "[2025] SGCA 12" in body
    assert "Court of Appeal" in body
    assert "2025-03-15" in body


# ===== longform mode (no aside) =====

@pytest.mark.asyncio
async def test_row_longform_mode_no_aside(client_row):
    r = await client_row.get("/sglawwatch/longform_articles/1")
    assert r.status_code == 200
    body = r.text
    assert 'class="article' in body  # article variant
    assert 'class="aside"' not in body  # longform has NO sidebar


# ===== catalogue-record fallback (no display.row_mode) =====

@pytest.mark.asyncio
async def test_row_tabular_fallback_renders_dl(client_row):
    r = await client_row.get("/sglawwatch/about_singapore_law/1")
    assert r.status_code == 200
    body = r.text
    assert "<dl" in body  # key-value list of short values


@pytest.mark.asyncio
async def test_row_tabular_never_renders_full_text(client_row):
    """INVERTED from the old <details> design: the protected long-text
    `content` column must NOT appear at all — no <details>, no preview."""
    r = await client_row.get("/sglawwatch/about_singapore_law/1")
    body = r.text
    assert "<details" not in body
    assert "Show full content" not in body
    assert SENTINEL not in body
    # short identifying values still render
    assert "Constitutional Law" in body
    assert "On the separation of powers" in body


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


@pytest.mark.asyncio
async def test_row_fragments_suffix_returns_404(client_row):
    r = await client_row.get("/zeeker-judgements/judgments_fragments/some-pk")
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

"""Phase 6 — /sql + /sql/{db} route integration tests (Plan 05).

Replaces the pytest.skip stubs from Plan 06-01 with real assertions exercising
the routes_sql.py handlers authored in Plan 06-05 Tasks 1+2.

Critical assertions pinned by Plan 06-05 contracts:
  - test_sql_db_post_400_error (T-06-05-03 / RESEARCH Pitfall 1) — Datasette
    400 with friendly `error` body MUST render inline as HTTP 200 with the
    .sql-error block; NEVER 503.
  - test_sql_db_post_param_binding (T-06-05-01) — :name params bound via
    `_param_<name>` URL keys; SQL string never mutated.
  - test_sql_db_post_drops_extra_form_fields (T-06-05-02) — querystring
    smuggling prevention. Fields outside the allowlist (sql,
    _sql_param_<valid_name> for names actually in the SQL) are dropped.
  - test_sql_db_truncation_banner (T-06-05-04 / D-08) — truncated=true
    response renders banner + CSV download link.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from zeeker_frontend.datasette_client import reset_metadata_cache
from zeeker_frontend.main import app
from zeeker_frontend.routes_sql import _detect_params


_FIXTURES = Path(__file__).parent / "fixtures"
_ITALIC_H1 = re.compile(r"<h1>.*?<em[^>]*>[^<]+</em>.*?</h1>", re.DOTALL)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


def _load(name: str):
    return json.loads((_FIXTURES / name).read_text())


def _mock_factory(*, success_response: dict | None = None,
                  error_400_response: dict | None = None,
                  capture: dict | None = None):
    """Return AsyncClient that:
    - GET /.json → list of dbs (datasette returns dict keyed by db name)
    - GET /sglawwatch.json (no sql) → table list
    - GET /sglawwatch.json?sql=…:
        if error_400_response set → 400 with that body
        else → 200 with success_response (default: 1-row {"a": 1})
    - GET /-/metadata.json → canned-queries fixture
    `capture` (if provided) records the last upstream params under capture['last_params'].
    """
    sglawwatch = _load("sglawwatch.json")
    metadata = _load("metadata_with_canned_queries.json")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        params = dict(request.url.params)
        # Only capture the SQL execution path (not metadata or db-list calls).
        # The handler calls fetch_site_metadata AFTER execute_sql, so without
        # this filter the capture would be overwritten by the metadata fetch.
        if capture is not None and path == "/sglawwatch.json" and "sql" in params:
            capture["last_path"] = path
            capture["last_params"] = params
        if path == "/.json":
            # Datasette returns dict {db_name: {hash, color, ...}, ...}
            return httpx.Response(200, json={
                "sglawwatch": {"hash": "x", "size": 100, "is_mutable": False},
            })
        if path == "/-/metadata.json":
            return httpx.Response(200, json=metadata)
        if path == "/sglawwatch.json":
            if "sql" in params:
                if error_400_response is not None:
                    return httpx.Response(400, json=error_400_response)
                return httpx.Response(
                    200,
                    json=success_response or {
                        "ok": True,
                        "rows": [{"a": 1}],
                        "columns": ["a"],
                        "truncated": False,
                        "query_ms": 1.0,
                        "error": None,
                    },
                )
            return httpx.Response(200, json=sglawwatch)
        return httpx.Response(404, json={"ok": False, "error": "not found"})

    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
async def client_sql():
    capture: dict = {}
    app.state.http = _mock_factory(capture=capture)
    app.state.searchable_tables = {}
    app.state.changelog = []
    app.state._sql_capture = capture
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.fixture
async def client_sql_400():
    err = _load("sql_error_400.json")
    app.state.http = _mock_factory(error_400_response=err)
    app.state.searchable_tables = {}
    app.state.changelog = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.fixture
async def client_sql_truncated():
    truncated = {
        "ok": True,
        "rows": [{"id": i, "title": f"row {i}"} for i in range(10)],
        "columns": ["id", "title"],
        "truncated": True,
        "query_ms": 28.4,
        "error": None,
    }
    app.state.http = _mock_factory(success_response=truncated)
    app.state.searchable_tables = {}
    app.state.changelog = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


# --- _detect_params unit test ---

def test_detect_params_regex():
    """Unit test of the :param detection regex (dedupe + encounter order)."""
    assert _detect_params("SELECT * FROM t WHERE id = :id") == ["id"]
    # Dedupe + preserve encounter order
    assert _detect_params("SELECT :a, :b, :a FROM t WHERE x = :b") == ["a", "b"]
    # No match for invalid name (starts with digit)
    assert _detect_params("SELECT :1bad") == []
    assert _detect_params("") == []
    assert _detect_params("SELECT 1") == []


# --- /sql landing tests ---

@pytest.mark.asyncio
async def test_sql_landing(client_sql):
    """GET /sql → 200, italic-accent H1, lists databases, sets cache header."""
    r = await client_sql.get("/sql")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    assert "Run" in r.text and "<em>SQL</em>" in r.text
    assert "/sql/sglawwatch" in r.text
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc and "stale-while-revalidate=300" in cc


@pytest.mark.asyncio
async def test_sql_landing_orientation_for_casual_researchers(client_sql):
    """Landing page surfaces orientation copy for casual researchers (HUMAN UAT).

    Required orientation surfaces:
      - "What this page is for" / "Reach for SQL when…" framing
      - Pointer to /search and / so they try lighter tools first
      - 3-second + 1,000-row limits surfaced before clicking into a database
      - Pointer to /how-to-use for SQL examples
    """
    r = await client_sql.get("/sql")
    body = r.text
    assert "What this page is for" in body
    assert "Reach for SQL when" in body
    assert "/search" in body  # try-search-first pointer
    assert "3-second" in body and "1,000 rows" in body
    assert "/how-to-use" in body


# --- GET /sql/{db} tests ---

@pytest.mark.asyncio
async def test_sql_db_get(client_sql):
    """GET /sql/{db} → 200, italic-accent H1, textarea, canned queries section."""
    r = await client_sql.get("/sql/sglawwatch")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    assert "<textarea" in r.text
    # Canned queries section present (fixture has at least one)
    assert "Saved queries" in r.text or "canned-query" in r.text


@pytest.mark.asyncio
async def test_sql_db_get_404(client_sql):
    """GET /sql/{unknown_db} → 404."""
    r = await client_sql.get("/sql/nonexistent")
    assert r.status_code == 404


# --- POST /sql/{db} tests ---

@pytest.mark.asyncio
async def test_sql_db_post_success(client_sql):
    """POST /sql/{db} with valid SQL → 200, results table rendered, no-store."""
    r = await client_sql.post("/sql/sglawwatch", data={"sql": "SELECT 1 as a"})
    assert r.status_code == 200
    assert "<table" in r.text
    cc = r.headers.get("cache-control", "")
    assert "no-store" in cc


@pytest.mark.asyncio
async def test_sql_db_post_400_error(client_sql_400):
    """T-06-05-03 / Pitfall 1 — Datasette 400 with error body must NOT 503; render inline."""
    r = await client_sql_400.post("/sql/sglawwatch", data={"sql": "SELECT * FROM nope"})
    assert r.status_code == 200, f"expected 200 with .sql-error block, got {r.status_code}"
    assert "no such table" in r.text or "Query error" in r.text


@pytest.mark.asyncio
async def test_sql_db_truncation_banner(client_sql_truncated):
    """T-06-05-04 — truncated=true response renders banner + CSV deep-link."""
    r = await client_sql_truncated.post("/sql/sglawwatch", data={"sql": "SELECT * FROM headlines"})
    assert r.status_code == 200
    assert "Showing" in r.text or "maximum" in r.text or "truncation" in r.text.lower()
    assert ".csv?sql=" in r.text  # CSV deep-link present


@pytest.mark.asyncio
async def test_sql_db_export_links(client_sql):
    """POST success → response body contains URL-encoded CSV + JSON deep-links."""
    r = await client_sql.post("/sql/sglawwatch", data={"sql": "SELECT 1"})
    assert r.status_code == 200
    # URL-encoded SQL in export anchors (Caddy suffix routes to datasette)
    assert "/sglawwatch.csv?sql=" in r.text
    assert "/sglawwatch.json?sql=" in r.text


@pytest.mark.asyncio
async def test_sql_db_post_param_binding(client_sql):
    """T-06-05-01 — :name params bound via _param_<name> URL key; SQL never mutated."""
    r = await client_sql.post(
        "/sql/sglawwatch",
        data={"sql": "SELECT * FROM t WHERE id = :id", "_sql_param_id": "42"},
    )
    assert r.status_code == 200
    capture = app.state._sql_capture
    assert capture["last_params"].get("_param_id") == "42"
    # The SQL string itself is forwarded verbatim — no concatenation of values.
    assert capture["last_params"].get("sql") == "SELECT * FROM t WHERE id = :id"
    # _shape always present (RESEARCH Pitfall 1)
    assert capture["last_params"].get("_shape") == "objects"


@pytest.mark.asyncio
async def test_sql_db_post_drops_extra_form_fields(client_sql):
    """T-06-05-02 — querystring smuggling prevention.

    Fields outside the allowlist (sql, _sql_param_<valid_name> for names
    appearing in SQL) MUST be dropped before reaching upstream datasette.
    """
    r = await client_sql.post(
        "/sql/sglawwatch",
        data={
            "sql": "SELECT 1",
            "extra": "evil",
            "allow_execute_sql": "true",
            "_sql_param_id": "ok",  # but :id NOT in SQL → dropped per detected_params filter
        },
    )
    assert r.status_code == 200
    capture = app.state._sql_capture
    assert "extra" not in capture["last_params"]
    assert "allow_execute_sql" not in capture["last_params"]
    # _param_id should NOT be present because :id not in the SQL string
    assert "_param_id" not in capture["last_params"]

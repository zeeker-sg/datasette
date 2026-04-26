"""Unit tests for Phase 6 datasette_client helpers.

Three helpers under test:
  - discover_searchable_tables  — one-shot FTS probe at lifespan boot
  - search_table                — wraps /{db}/{table}.json?_search=...
  - execute_sql                 — wraps /{db}.json?sql=...&_param_*=...

All tests use httpx.MockTransport so no FastAPI app boot is required.
Mirrors the test pattern in test_datasette_client_table_row.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from zeeker_frontend.datasette_client import (
    discover_searchable_tables,
    execute_sql,
    search_table,
)


_FIXTURES = Path(__file__).parent / "fixtures"


def _mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


# ---- discover_searchable_tables ----


@pytest.mark.asyncio
async def test_discover_searchable_extracts_fts_table():
    """Tables with `fts_table` populated AND not hidden AND not _zeeker-prefixed
    are surfaced; tables with fts_table=None are filtered."""

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path == "/.json":
            return httpx.Response(
                200,
                json={
                    "sglawwatch": {"path": "sglawwatch"},
                    "Zeeker-Judgements": {"path": "Zeeker-Judgements"},
                },
            )
        if path == "/sglawwatch.json":
            return httpx.Response(
                200,
                json={
                    "tables": [
                        {"name": "headlines", "hidden": False, "fts_table": "headlines_fts"},
                        {"name": "categories", "hidden": False, "fts_table": None},
                    ]
                },
            )
        if path == "/Zeeker-Judgements.json":
            return httpx.Response(
                200,
                json={
                    "tables": [
                        {"name": "judgments", "hidden": False, "fts_table": "judgments_fts"},
                    ]
                },
            )
        return httpx.Response(404, json={"ok": False})

    async with _mock(handler) as c:
        result = await discover_searchable_tables(c)

    assert result == {
        "sglawwatch": ["headlines"],
        "Zeeker-Judgements": ["judgments"],
    }


@pytest.mark.asyncio
async def test_discover_searchable_filters_zeeker_prefix():
    """RESEARCH Pitfall 4 — _zeeker_* platform tables can have hidden=False
    in some overlays; the prefix predicate is mandatory."""

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path == "/.json":
            return httpx.Response(200, json={"sglawwatch": {"path": "sglawwatch"}})
        if path == "/sglawwatch.json":
            return httpx.Response(
                200,
                json={
                    "tables": [
                        {"name": "headlines", "hidden": False, "fts_table": "headlines_fts"},
                        # _zeeker_schemas with hidden=False AND fts_table set must STILL be filtered
                        {"name": "_zeeker_schemas", "hidden": False, "fts_table": "schemas_fts"},
                    ]
                },
            )
        return httpx.Response(404, json={"ok": False})

    async with _mock(handler) as c:
        result = await discover_searchable_tables(c)

    assert result == {"sglawwatch": ["headlines"]}
    assert "_zeeker_schemas" not in result.get("sglawwatch", [])


@pytest.mark.asyncio
async def test_discover_searchable_filters_hidden():
    """Tables with hidden=True (e.g. *_fts internal tables) MUST be filtered
    even if fts_table is set."""

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path == "/.json":
            return httpx.Response(200, json={"sglawwatch": {"path": "sglawwatch"}})
        if path == "/sglawwatch.json":
            return httpx.Response(
                200,
                json={
                    "tables": [
                        {"name": "headlines", "hidden": False, "fts_table": "headlines_fts"},
                        # FTS internal table — hidden=True; fts_table=self
                        {"name": "headlines_fts", "hidden": True, "fts_table": "headlines_fts"},
                    ]
                },
            )
        return httpx.Response(404, json={"ok": False})

    async with _mock(handler) as c:
        result = await discover_searchable_tables(c)

    assert result == {"sglawwatch": ["headlines"]}
    assert "headlines_fts" not in result.get("sglawwatch", [])


# ---- search_table ----


@pytest.mark.asyncio
async def test_search_table_passes_q_and_size():
    captured = {}

    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        captured["path"] = req.url.path
        with open(_FIXTURES / "headlines_search_results.json") as f:
            return httpx.Response(200, json=json.load(f))

    async with _mock(h) as c:
        result = await search_table(c, "sglawwatch", "headlines", "DBS", 10)

    assert captured["path"] == "/sglawwatch/headlines.json"
    assert captured["params"]["_search"] == "DBS"
    assert captured["params"]["_size"] == "10"
    assert captured["params"]["_shape"] == "objects"
    # Real fixture loads — primary_keys + filtered_table_rows_count survive
    assert result is not None
    assert result["primary_keys"] == ["id"]
    assert result["filtered_table_rows_count"] == 12


@pytest.mark.asyncio
async def test_search_table_404_returns_none():
    async with _mock(lambda r: httpx.Response(404, json={})) as c:
        assert await search_table(c, "db", "tbl", "q", 10) is None


# ---- execute_sql ----


@pytest.mark.asyncio
async def test_execute_sql_builds_param_url():
    """Params dict {"id": "42"} → URL key _param_id=42; sql NEVER concatenated."""
    captured = {}

    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        captured["path"] = req.url.path
        return httpx.Response(
            200,
            json={"ok": True, "rows": [{"id": "42"}], "columns": ["id"], "error": None},
        )

    async with _mock(h) as c:
        body, error = await execute_sql(c, "sglawwatch", "SELECT :id", {"id": "42"})

    assert captured["path"] == "/sglawwatch.json"
    assert captured["params"]["sql"] == "SELECT :id"
    assert captured["params"]["_param_id"] == "42"
    assert captured["params"]["_shape"] == "objects"
    assert error is None
    assert body is not None
    assert body["rows"] == [{"id": "42"}]


@pytest.mark.asyncio
async def test_execute_sql_400_returns_friendly_error():
    """RESEARCH Pitfall 1 — datasette returns 400 with populated `error` field;
    handler MUST read body BEFORE raise_for_status()."""
    with open(_FIXTURES / "sql_error_400.json") as f:
        error_body = json.load(f)

    async with _mock(lambda r: httpx.Response(400, json=error_body)) as c:
        body, error = await execute_sql(c, "sglawwatch", "SELECT * FROM nope")

    assert body is None
    assert error is not None
    assert "no such table" in error


@pytest.mark.asyncio
async def test_execute_sql_404_returns_db_not_found():
    async with _mock(lambda r: httpx.Response(404, json={"ok": False})) as c:
        body, error = await execute_sql(c, "missing", "SELECT 1")

    assert body is None
    assert error == "Database not found"


@pytest.mark.asyncio
async def test_execute_sql_shape_objects_always_set():
    """Even when params=None, _shape=objects MUST be present."""
    captured = {}

    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        return httpx.Response(
            200,
            json={"ok": True, "rows": [], "columns": [], "error": None},
        )

    async with _mock(h) as c:
        await execute_sql(c, "sglawwatch", "SELECT 1")

    assert captured["params"]["_shape"] == "objects"
    assert captured["params"]["sql"] == "SELECT 1"


@pytest.mark.asyncio
async def test_execute_sql_non_json_response_returns_friendly_error():
    """WR-02 — if upstream returns HTML (Caddy 502, datasette error page,
    network MITM page) instead of JSON, surface a clean error string
    instead of letting ValueError propagate as an unhandled 500."""
    async with _mock(
        lambda r: httpx.Response(
            200,
            content=b"<html><body>502 Bad Gateway</body></html>",
            headers={"content-type": "text/html"},
        )
    ) as c:
        body, error = await execute_sql(c, "sglawwatch", "SELECT 1")

    assert body is None
    assert error is not None
    assert "non-JSON" in error or "JSON" in error

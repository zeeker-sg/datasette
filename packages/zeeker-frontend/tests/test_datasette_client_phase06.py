"""Unit tests for Phase 6 datasette_client helpers.

Two helpers under test (execute_sql was removed with the /sql editor):
  - discover_searchable_tables  — one-shot FTS probe at lifespan boot
  - search_table                — wraps /{db}/{table}.json?_search=...

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


@pytest.mark.asyncio
async def test_discover_searchable_filters_fragments_tables():
    """*_fragments chunk tables carry full text copies — they must never be
    a search surface, even when hidden=False and FTS-enabled."""

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
                        {
                            "name": "about_singapore_law_fragments",
                            "hidden": False,
                            "fts_table": "about_singapore_law_fragments_fts",
                        },
                    ]
                },
            )
        return httpx.Response(404, json={"ok": False})

    async with _mock(handler) as c:
        result = await discover_searchable_tables(c)

    assert result == {"sglawwatch": ["headlines"]}


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


# ---- execute_sql tests removed with the /sql editor (catalogue posture) ----

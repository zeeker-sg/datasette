"""Unit tests for fetch_table + fetch_row — MockTransport-driven, no FastAPI app."""
from __future__ import annotations

import httpx
import pytest

from zeeker_frontend.datasette_client import fetch_table, fetch_row


def _mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


# ---- fetch_table ----

@pytest.mark.asyncio
async def test_fetch_table_always_adds_shape_objects():
    captured = {}
    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rows": [], "columns": []})
    async with _mock(h) as c:
        await fetch_table(c, "db", "tbl")
    assert captured["params"]["_shape"] == "objects"


@pytest.mark.asyncio
async def test_fetch_table_allows_known_datasette_params():
    captured = {}
    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rows": []})
    async with _mock(h) as c:
        await fetch_table(c, "db", "tbl", {
            "_size": "10", "_sort": "date", "_search": "foo",
            "_facet": "category", "_next": "abc",
        })
    for k in ("_size", "_sort", "_search", "_facet", "_next"):
        assert captured["params"][k]


@pytest.mark.asyncio
async def test_fetch_table_drops_unknown_underscore_params():
    # Pitfall 7 — _extras, _internal, allow_execute_sql must be dropped
    captured = {}
    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rows": []})
    async with _mock(h) as c:
        await fetch_table(c, "db", "tbl", {
            "_extras": "foreign_key_tables",
            "_internal": "anything",
            "_size": "10",
        })
    assert "_extras" not in captured["params"]
    assert "_internal" not in captured["params"]
    assert captured["params"]["_size"] == "10"


@pytest.mark.asyncio
async def test_fetch_table_allows_plain_column_filter():
    captured = {}
    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rows": []})
    async with _mock(h) as c:
        await fetch_table(c, "db", "tbl", {"category": "Straits Times"})
    assert captured["params"]["category"] == "Straits Times"


@pytest.mark.asyncio
async def test_fetch_table_allows_column_operator_filter():
    captured = {}
    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rows": []})
    async with _mock(h) as c:
        await fetch_table(c, "db", "tbl", {"date__gte": "2025-01-01"})
    assert captured["params"]["date__gte"] == "2025-01-01"


@pytest.mark.asyncio
async def test_fetch_table_404_returns_none():
    async with _mock(lambda r: httpx.Response(404, json={"ok": False})) as c:
        assert await fetch_table(c, "db", "tbl") is None


@pytest.mark.asyncio
async def test_fetch_table_500_raises():
    async with _mock(lambda r: httpx.Response(500, json={})) as c:
        with pytest.raises(httpx.HTTPError):
            await fetch_table(c, "db", "tbl")


@pytest.mark.asyncio
async def test_fetch_table_returns_payload_on_200():
    payload = {"rows": [{"id": 1}], "columns": ["id"]}
    async with _mock(lambda r: httpx.Response(200, json=payload)) as c:
        r = await fetch_table(c, "db", "tbl")
    assert r == payload


# ---- fetch_row ----

@pytest.mark.asyncio
async def test_fetch_row_always_adds_shape_objects():
    captured = {}
    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        captured["path"] = req.url.path
        return httpx.Response(200, json={"rows": [{"id": 1}]})
    async with _mock(h) as c:
        await fetch_row(c, "db", "tbl", "abc123")
    assert captured["params"]["_shape"] == "objects"
    assert captured["path"] == "/db/tbl/abc123.json"


@pytest.mark.asyncio
async def test_fetch_row_404_returns_none():
    async with _mock(lambda r: httpx.Response(404, json={})) as c:
        assert await fetch_row(c, "db", "tbl", "missing-pk") is None


@pytest.mark.asyncio
async def test_fetch_row_500_raises():
    async with _mock(lambda r: httpx.Response(500, json={})) as c:
        with pytest.raises(httpx.HTTPError):
            await fetch_row(c, "db", "tbl", "any")


@pytest.mark.asyncio
async def test_fetch_row_returns_payload_on_200():
    payload = {"rows": [{"id": 1, "title": "x"}], "columns": ["id", "title"]}
    async with _mock(lambda r: httpx.Response(200, json=payload)) as c:
        r = await fetch_row(c, "db", "tbl", "1")
    assert r == payload

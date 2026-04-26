"""Phase 6 — auxiliary route integration tests (Plan 03).

Exercises GET /developers, /status, /sources, /about, /how-to-use, /llms.txt,
/robots.txt via ASGITransport + MockTransport.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from zeeker_frontend.main import app
from zeeker_frontend.datasette_client import reset_metadata_cache


_FIXTURES = Path(__file__).parent / "fixtures"

_ITALIC_H1 = re.compile(r"<h1>.*?<em[^>]*>[^<]+</em>.*?</h1>", re.DOTALL)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


def _load(name: str):
    return json.loads((_FIXTURES / name).read_text())


def _mock_datasette(*, raise_on=None):
    sglawwatch = _load("sglawwatch.json")
    metadata = _load("metadata.json")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if raise_on and raise_on in path:
            raise httpx.ConnectError("simulated upstream failure")
        if path == "/.json":
            return httpx.Response(
                200,
                json={
                    "sglawwatch": {
                        "name": "sglawwatch",
                        "size": 1234567,
                        "is_mutable": False,
                        "hash": "abc",
                        "tables_count": 3,
                    }
                },
            )
        if path == "/sglawwatch.json":
            return httpx.Response(200, json=sglawwatch)
        if path == "/-/metadata.json":
            return httpx.Response(200, json=metadata)
        return httpx.Response(404, json={"ok": False, "error": "Not found"})

    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture
async def client_aux():
    app.state.http = _mock_datasette()
    app.state.changelog = [
        {"date": "2025-06-09", "type": "feature", "title": "Launch", "description": "hi"},
        {"date": "2025-05-16", "type": "data", "title": "headlines", "description": "ok"},
    ]
    app.state.searchable_tables = {}  # not exercised in aux tests
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.fixture
async def client_aux_503():
    """Lifespan-mocked client that raises ConnectError on every datasette call."""
    app.state.http = _mock_datasette(raise_on="/")  # match every path → connect error
    app.state.changelog = []
    app.state.searchable_tables = {}
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()


@pytest.mark.asyncio
async def test_developers_renders(client_aux):
    r = await client_aux.get("/developers")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    assert "/static/css/zeeker.css" in r.text
    assert "_zeeker" not in r.text


@pytest.mark.asyncio
async def test_status_renders(client_aux):
    r = await client_aux.get("/status")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    assert "Launch" in r.text  # changelog title surfaces
    assert "max-age=60" in r.headers.get("cache-control", "")
    assert "stale-while-revalidate=300" in r.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_sources_hides_internal(client_aux):
    r = await client_aux.get("/sources")
    assert r.status_code == 200
    assert "_zeeker" not in r.text


@pytest.mark.asyncio
async def test_about_renders(client_aux):
    r = await client_aux.get("/about")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    # M1 stale link fixed: /-/metadata → /developers
    assert "/-/metadata" not in r.text
    assert "/developers" in r.text


@pytest.mark.asyncio
async def test_how_to_use_re_pointed(client_aux):
    r = await client_aux.get("/how-to-use")
    assert r.status_code == 200
    assert _ITALIC_H1.search(r.text)
    # Phase 6 D-01: every M1 /-/search reference re-points to /search
    assert "/-/search" not in r.text


@pytest.mark.asyncio
async def test_llms_txt_format(client_aux):
    r = await client_aux.get("/llms.txt")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/plain")
    assert r.text.startswith("# data.zeeker.sg")
    assert "_zeeker" not in r.text


@pytest.mark.asyncio
async def test_robots_txt(client_aux):
    r = await client_aux.get("/robots.txt")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/plain")
    assert "User-agent: GPTBot" in r.text


@pytest.mark.asyncio
async def test_aux_cache_control(client_aux):
    """Every cacheable GET sets max-age=60 + stale-while-revalidate=300 (D-14)."""
    for route in ["/developers", "/status", "/sources", "/about", "/how-to-use", "/llms.txt"]:
        r = await client_aux.get(route)
        cc = r.headers.get("cache-control", "")
        assert "max-age=60" in cc, f"{route}: cache-control={cc!r}"
        assert "stale-while-revalidate=300" in cc, f"{route}: cache-control={cc!r}"


@pytest.mark.asyncio
async def test_developers_503_on_upstream_error(client_aux_503):
    r = await client_aux_503.get("/developers")
    assert r.status_code == 503

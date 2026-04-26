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
    # Phase 6 D-01: every M1 reference to Datasette's HTML search UI must
    # re-point to the frontend's /search. The Datasette JSON API alternative
    # (/-/search.json) IS allowed — it's the documented programmatic export
    # path on /how-to-use after the Phase-6 URL accuracy audit. So this
    # check is precise about what's forbidden: a link/form pointing at the
    # bare /-/search HTML route.
    body = r.text
    assert 'href="/-/search"' not in body
    assert 'action="/-/search"' not in body
    assert "/-/search?" not in body  # query-string form of the HTML UI


@pytest.mark.asyncio
async def test_how_to_use_documents_only_working_urls(client_aux):
    """URL accuracy audit (HUMAN UAT) — every URL pattern listed in the
    /how-to-use copy must resolve against the live API contract.

    Live live-curl check at the time of this commit established:
      /search.csv  → 404 (frontend /search is HTML-only)
      /search.json → 404 (same)
      /{db}.db     → 403 (allow_download config gap, separate follow-up)

    These three patterns must NOT ship in /how-to-use copy. The doc was
    rewritten to advertise /-/search.json (Datasette-native, returns 200)
    as the JSON-API search alternative, and to drop the .db whole-database
    download claim until the metadata.json allow_download config is
    extended to named databases.
    """
    r = await client_aux.get("/how-to-use")
    body = r.text
    # Broken endpoints — must NOT be advertised. Substrings are precise to
    # avoid false matches on /-/search.json (which IS allowed and contains
    # /search.json as a substring).
    assert "/search.csv?" not in body
    assert " /search.json" not in body and "(/search.json" not in body
    assert "/{database}.db" not in body
    # Correct alternatives advertised
    assert "/-/search.json" in body
    assert "/{database}/{table}.csv" in body
    assert "/{database}.csv?sql=" in body


@pytest.mark.asyncio
async def test_how_to_use_button_consistency_option_2(client_aux):
    """Option 2 button policy — only the terminal CTA card carries buttons.

    HUMAN UAT — visitor feedback was that mid-page method-cards had buttons
    on some but not others (Try Global Search, Browse Databases, Try a Search,
    hello@zeeker.sg) which read as inconsistent. The page now strips every
    mid-page button and concentrates all action onto a single terminal
    `Ready to start?` card mirroring /about's pattern.
    """
    r = await client_aux.get("/how-to-use")
    body = r.text
    # Terminal CTA card present, with the canonical action triad.
    assert "cta-section" in body
    assert "Ready to start?" in body
    assert ">Try Global Search<" in body
    assert ">Open the SQL Editor<" in body
    assert ">Browse Databases<" in body
    # Mid-page buttons are gone — these literal copies should no longer ship
    # outside the terminal CTA. (`>Try Global Search<` survives only inside
    # the CTA card, asserted above; the regressed mid-page buttons used
    # different copy.)
    assert ">Try a Search<" not in body  # was on §2 Track Developments
    # Email is now an inline link in prose, not a standalone button.
    assert 'class="btn btn-primary">hello@zeeker.sg' not in body
    assert 'href="mailto:hello@zeeker.sg"' in body  # but still reachable


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

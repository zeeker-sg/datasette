"""Unit tests for zeeker_frontend.datasette_client using MockTransport."""
import pytest

from zeeker_frontend.datasette_client import (
    fetch_databases, fetch_database, fetch_site_metadata, reset_metadata_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


@pytest.mark.asyncio
async def test_fetch_databases_returns_list(mock_datasette):
    async with mock_datasette as client:
        dbs = await fetch_databases(client)
    assert isinstance(dbs, list)
    assert all(isinstance(d, dict) for d in dbs)
    assert all("name" in d for d in dbs)
    # All 3 db names from the captured fixture
    names = {d["name"] for d in dbs}
    assert {"sglawwatch", "sg-gov-newsrooms", "zeeker-judgements"}.issubset(names)


@pytest.mark.asyncio
async def test_fetch_database_200(mock_datasette):
    async with mock_datasette as client:
        payload = await fetch_database(client, "sglawwatch")
    assert payload is not None
    assert "tables" in payload
    assert any(t["name"] == "headlines" for t in payload["tables"])


@pytest.mark.asyncio
async def test_fetch_database_404(mock_datasette):
    async with mock_datasette as client:
        payload = await fetch_database(client, "nonexistent-database")
    assert payload is None


@pytest.mark.asyncio
async def test_fetch_site_metadata_caches(mock_datasette):
    """Second call within TTL window should be served from cache.

    MockTransport call count is implicit — we track it through the handler."""
    import httpx

    call_count = {"n": 0}

    def counting_handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        return httpx.Response(200, json={"title": "test", "databases": {}})

    async with httpx.AsyncClient(
        base_url="http://x", transport=httpx.MockTransport(counting_handler)
    ) as client:
        a = await fetch_site_metadata(client)
        b = await fetch_site_metadata(client)

    assert a == b
    assert call_count["n"] == 1  # cached


@pytest.mark.asyncio
async def test_fetch_site_metadata_swallows_error():
    import httpx

    def erroring_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    async with httpx.AsyncClient(
        base_url="http://x", transport=httpx.MockTransport(erroring_handler)
    ) as client:
        result = await fetch_site_metadata(client)

    assert result == {}

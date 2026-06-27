"""
Tests for the cache_headers plugin.
Verifies that Cache-Control headers are set correctly for different route types.
"""

import pytest


def make_scope(path, method="GET"):
    return {
        "type": "http",
        "method": method,
        "path": path,
    }


async def collect_response(app, scope):
    """Run the ASGI app and collect the response start event headers."""
    received_headers = {}

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(event):
        if event["type"] == "http.response.start":
            received_headers.update(
                {k.decode(): v.decode() for k, v in event.get("headers", [])}
            )

    await app(scope, receive, send)
    return received_headers


class MockDatasette:
    pass


@pytest.fixture
def wrapped_app():
    """Build the ASGI wrapper around a minimal no-op app."""
    from plugins.cache_headers import asgi_wrapper

    async def noop_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"cache-control", b"max-age=5"),  # Datasette's default
                    (b"content-type", b"text/html"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    wrapper = asgi_wrapper(MockDatasette())
    return wrapper(noop_app)


@pytest.mark.asyncio
async def test_html_page_gets_public_cache_control(wrapped_app):
    headers = await collect_response(wrapped_app, make_scope("/sglawwatch/headlines"))
    cc = headers.get("cache-control", "")
    assert "public" in cc
    assert "s-maxage=3600" in cc
    assert "max-age=300" in cc


@pytest.mark.asyncio
async def test_static_asset_gets_long_cache(wrapped_app):
    headers = await collect_response(wrapped_app, make_scope("/static/css/zeeker-base.css"))
    cc = headers.get("cache-control", "")
    assert "public" in cc
    assert "s-maxage=86400" in cc
    assert "max-age=86400" in cc


@pytest.mark.asyncio
async def test_internal_routes_not_cached(wrapped_app):
    headers = await collect_response(wrapped_app, make_scope("/-/versions.json"))
    cc = headers.get("cache-control", "")
    assert "no-store" in cc


@pytest.mark.asyncio
async def test_post_request_not_modified(wrapped_app):
    """POST requests should pass through unchanged (no cache-control override)."""
    headers = await collect_response(wrapped_app, make_scope("/", method="POST"))
    # Should still have the original max-age=5 from the noop app
    cc = headers.get("cache-control", "")
    assert cc == "max-age=5"


@pytest.mark.asyncio
async def test_api_json_endpoint_cached(wrapped_app):
    headers = await collect_response(wrapped_app, make_scope("/sglawwatch/headlines.json"))
    cc = headers.get("cache-control", "")
    assert "public" in cc
    assert "s-maxage=3600" in cc


@pytest.mark.asyncio
async def test_homepage_cached(wrapped_app):
    headers = await collect_response(wrapped_app, make_scope("/"))
    cc = headers.get("cache-control", "")
    assert "public" in cc
    assert "s-maxage=3600" in cc


@pytest.mark.asyncio
async def test_original_cache_control_replaced(wrapped_app):
    """Datasette's default max-age=5 should be replaced, not appended."""
    headers = await collect_response(wrapped_app, make_scope("/sglawwatch"))
    cc = headers.get("cache-control", "")
    # Should not contain the original max-age=5
    assert "max-age=5" not in cc


def make_error_app(status):
    async def error_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"cache-control", b"max-age=5"),
                    (b"content-type", b"text/plain"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"error"})

    from plugins.cache_headers import asgi_wrapper

    return asgi_wrapper(MockDatasette())(error_app)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [301, 403, 404, 500])
async def test_non_2xx_responses_get_no_store(status):
    """Non-2xx responses (403 lockdowns, errors) must never be CDN-cached."""
    app = make_error_app(status)
    headers = await collect_response(app, make_scope("/sglawwatch/headlines.json"))
    assert headers.get("cache-control") == "no-store"


@pytest.mark.asyncio
async def test_2xx_response_still_cached():
    app = make_error_app(200)
    headers = await collect_response(app, make_scope("/sglawwatch/headlines.json"))
    cc = headers.get("cache-control", "")
    assert "public" in cc
    assert "no-store" not in cc


@pytest.mark.asyncio
async def test_authorized_requests_never_cached(wrapped_app):
    """Owner-token responses can carry full protected content for URLs
    anonymous users also hit — they must never enter the shared CDN cache."""
    scope = make_scope("/sglawwatch/headlines.json")
    scope["headers"] = [(b"authorization", b"Bearer anything")]
    headers = await collect_response(wrapped_app, scope)
    cc = headers.get("cache-control", "")
    assert "no-store" in cc
    assert "private" in cc
    assert "public" not in cc

# plugins/cache_headers.py
"""
Sets Cache-Control headers so Cloudflare (and other CDNs) cache responses.

Strategy:
- Static assets (/static/*): public, 24h browser + CDN
- HTML pages and API endpoints: public, 5min browser + 1h CDN (s-maxage)
- Internal Datasette routes (/-/):  no caching
- Non-GET methods: no caching
"""

import functools

from datasette import hookimpl

# Routes that should never be cached
NO_CACHE_PREFIXES = ("/-/",)

# Static assets can be cached much longer
STATIC_PREFIX = "/static/"

# CDN TTL (s-maxage) for pages and API responses — 1 hour
# Data refreshes ~every 3 hours, so worst-case staleness is 1 hour
CDN_TTL = 3600

# Browser TTL (max-age) for pages and API responses — 5 minutes
BROWSER_TTL = 300

# TTL for static assets (CSS, JS, fonts) — 24 hours
STATIC_TTL = 86400


def _has_authorization_header(scope):
    return any(
        name.lower() == b"authorization"
        for name, _ in scope.get("headers") or []
    )


@hookimpl
def asgi_wrapper(datasette):
    def wrap_with_cache_headers(app):
        @functools.wraps(app)
        async def add_cache_headers(scope, receive, send):
            if scope["type"] != "http":
                await app(scope, receive, send)
                return

            method = scope.get("method", "GET")
            path = scope.get("path", "")

            # Only cache GET requests
            if method != "GET":
                await app(scope, receive, send)
                return

            # Determine cache policy for this path
            if _has_authorization_header(scope):
                # Authenticated (owner-token) responses may contain full
                # protected content for the same URL anonymous users hit —
                # they must NEVER enter the shared CDN cache, or the cached
                # full variant would be served to everyone.
                cache_header = "no-store, private"
            elif any(path.startswith(prefix) for prefix in NO_CACHE_PREFIXES):
                cache_header = "no-store"
            elif path.startswith(STATIC_PREFIX):
                cache_header = f"public, max-age={STATIC_TTL}, s-maxage={STATIC_TTL}"
            else:
                cache_header = f"public, max-age={BROWSER_TTL}, s-maxage={CDN_TTL}"

            async def send_with_cache_headers(event):
                if event["type"] == "http.response.start":
                    status = event.get("status", 200)
                    # Never cache non-2xx responses (403s from the
                    # strip-columns content lockdown, 404s, 5xx, redirects)
                    # — a CDN-cached error would mask recovery and a cached
                    # 403 body is pointless to serve for an hour.
                    if 200 <= status < 300:
                        effective_header = cache_header
                    else:
                        effective_header = "no-store"
                    headers = list(event.get("headers", []))
                    # Remove existing Cache-Control header (Datasette sets max-age=5)
                    headers = [
                        (k, v) for k, v in headers
                        if k.lower() != b"cache-control"
                    ]
                    headers.append((b"cache-control", effective_header.encode()))
                    event = {**event, "headers": headers}
                await send(event)

            await app(scope, receive, send_with_cache_headers)

        return add_cache_headers

    return wrap_with_cache_headers

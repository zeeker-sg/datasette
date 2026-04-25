"""Thin datasette HTTP client + 60s TTL cache on /-/metadata.json.

Design per RESEARCH §"Pattern 2: Thin Handler + Graceful Error" and
§"Don't Hand-Roll" (cachetools not worth a new dep for one cache key).
"""
from __future__ import annotations

import time
from typing import Any

import httpx


_METADATA_CACHE: dict[str, Any] = {"payload": None, "expires_at": 0.0}
_METADATA_TTL_SECONDS = 60.0


async def fetch_databases(client: httpx.AsyncClient) -> list[dict]:
    """GET /.json → list of database dicts with `name` key promoted.

    Datasette returns {db_name: {hash, color, path, tables_count, ...}, ...}.
    We normalize into a list so Jinja iteration is linear.
    """
    r = await client.get("/.json")
    r.raise_for_status()
    raw = r.json()
    return [{"name": k, **v} for k, v in raw.items()]


async def fetch_database(client: httpx.AsyncClient, db: str) -> dict | None:
    """GET /{db}.json → payload dict, or None on 404.

    Per RESEARCH Pitfall 1: check 404 BEFORE raise_for_status() so callers
    can distinguish "database missing" from "upstream server error".
    """
    r = await client.get(f"/{db}.json")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def fetch_site_metadata(client: httpx.AsyncClient) -> dict:
    """GET /-/metadata.json with 60s TTL cache; empty dict on transport error."""
    now = time.monotonic()
    if _METADATA_CACHE["payload"] is not None and now < _METADATA_CACHE["expires_at"]:
        return _METADATA_CACHE["payload"]
    try:
        r = await client.get("/-/metadata.json")
        r.raise_for_status()
        payload = r.json()
    except httpx.HTTPError:
        return {}
    _METADATA_CACHE["payload"] = payload
    _METADATA_CACHE["expires_at"] = now + _METADATA_TTL_SECONDS
    return payload


def reset_metadata_cache() -> None:
    """Test helper — clear the cache between tests."""
    _METADATA_CACHE["payload"] = None
    _METADATA_CACHE["expires_at"] = 0.0


# Phase 5 — table + row endpoint helpers.
# Allowlist per RESEARCH §Pitfall 7 (querystring smuggling): only forward
# known datasette params + plain column-name filters + column__operator.
_TABLE_ALLOWED_PARAMS = frozenset({
    "_size", "_sort", "_sort_desc", "_search", "_next",
    "_facet", "_facet_array", "_facet_date",
})


async def fetch_table(
    client: httpx.AsyncClient,
    db: str,
    table: str,
    params: dict | None = None,
) -> dict | None:
    """GET /{db}/{table}.json with allowlisted params; None on 404, raises on other errors.

    Always passes _shape=objects so upstream rows are dicts keyed by column
    name (RESEARCH Pitfall 1). Drops unknown query keys to close the SSRF-ish
    querystring-smuggling surface (Pitfall 7).
    """
    safe_params: dict[str, Any] = {"_shape": "objects"}
    for k, v in (params or {}).items():
        if k in _TABLE_ALLOWED_PARAMS:
            safe_params[k] = v
        elif "__" in k:           # column__exact, column__contains, etc.
            safe_params[k] = v
        elif not k.startswith("_"):  # plain column-name filters
            safe_params[k] = v
        # else: silently drop (e.g. _extras, _internal, allow_execute_sql)
    r = await client.get(f"/{db}/{table}.json", params=safe_params)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def fetch_row(
    client: httpx.AsyncClient,
    db: str,
    table: str,
    pk: str,
) -> dict | None:
    """GET /{db}/{table}/{pk}.json — single row; None on 404."""
    r = await client.get(f"/{db}/{table}/{pk}.json", params={"_shape": "objects"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

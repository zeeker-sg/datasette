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


# ── Hidden-table conventions ───────────────────────────────────────────
# Platform conventions that should ALWAYS be hidden, regardless of what
# metadata.json says.  These are zeeker-specific (not Datasette internals):
#
#   _zeeker_*       — platform metadata tables (_zeeker_schemas, _zeeker_updates)
#   *_fragments     — row-chunk fragments for long-text search indexing
#
# Datasette's own FTS shadow tables (*_fts, *_fts_data, …) are already
# marked hidden=true by Datasette itself, but we list them here too so
# the guard in routes_table / routes_row (which checks by name before
# hitting the API) catches them.
_HIDDEN_TABLE_PREFIXES = ("_zeeker",)
_HIDDEN_TABLE_SUFFIXES = (
    "_fragments",
    "_fragments_fts", "_fragments_fts_data", "_fragments_fts_idx",
    "_fragments_fts_docsize", "_fragments_fts_config",
    "_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config",
)


def is_hidden_table(name: str) -> bool:
    """True if a table should be hidden from the UI based on platform naming
    conventions — independent of Datasette's ``hidden`` metadata flag.

    Covers ``_zeeker_*`` platform tables, ``*_fragments`` chunk tables (and
    their FTS shadows), and Datasette FTS internals.  Use alongside the
    ``hidden`` flag from the API payload: a table is visible only when
    ``not t.get("hidden") and not is_hidden_table(t["name"])``.
    """
    return (
        name.startswith(_HIDDEN_TABLE_PREFIXES)
        or name.endswith(_HIDDEN_TABLE_SUFFIXES)
    )


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


# ============================================================
# Phase 6 — FTS discovery + execution helpers
# ============================================================


async def discover_searchable_tables(
    client: httpx.AsyncClient,
) -> dict[str, list[str]]:
    """Return {db_name: [table_names_with_fts]}.

    One-shot probe at lifespan boot (RESEARCH §Pattern 2 / D-04). Each table
    dict on /{db}.json carries an `fts_table` field (string when FTS is
    available, None otherwise — verified live).

    Filtering predicates (mandatory, both required — RESEARCH Pitfall 4):
      - `t.get("hidden")` — drops *_fts internal virtual tables
      - `is_hidden_table(name)` — drops `_zeeker_*` platform tables and
        `*_fragments` chunk tables which can have hidden=False in some
        overlays

    Boot tolerance (RESEARCH Pitfall 10): any httpx error → empty dict.
    routes_search renders 503 friendly when cache empty AND q non-empty.
    """
    out: dict[str, list[str]] = {}
    try:
        dbs = await fetch_databases(client)
    except httpx.HTTPError:
        return out
    for entry in dbs:
        db = entry.get("name")
        if not db:
            continue
        try:
            payload = await fetch_database(client, db)
        except httpx.HTTPError:
            continue
        if payload is None:
            continue
        names: list[str] = []
        for t in payload.get("tables") or []:
            if t.get("hidden"):
                continue
            if is_hidden_table(t.get("name", "")):
                continue
            if t.get("fts_table"):
                names.append(t["name"])
        if names:
            out[db] = names
    return out


async def search_table(
    client: httpx.AsyncClient,
    db: str,
    table: str,
    q: str,
    size: int = 10,
) -> dict | None:
    """GET /{db}/{table}.json?_search=q&_size=size&_shape=objects.

    Returns the JSON body on 200, None on 404, raises on other HTTP errors.
    Always sends _shape=objects (RESEARCH Pitfall 1) so callers receive
    column-keyed row dicts.
    """
    r = await client.get(
        f"/{db}/{table}.json",
        params={"_search": q, "_size": size, "_shape": "objects"},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def execute_sql(
    client: httpx.AsyncClient,
    db: str,
    sql: str,
    params: dict[str, Any] | None = None,
) -> tuple[dict | None, str | None]:
    """Execute read-only SQL against /{db}.json?sql=…&_param_<name>=…

    Returns (body, error):
      - (body, None)           on 200 with body.error null/missing
      - (body, body.error)     on 200 with body.error populated (rare)
      - (None, body.error)     on 400 — Datasette's friendly SQL error
      - (None, "Database not found")  on 404
      - raises httpx.HTTPError on 5xx

    Always sends _shape=objects. Binds params via `_param_<name>` URL keys
    (NEVER concatenates values into the SQL string — RESEARCH Pitfall 7 /
    threat T-06-02-01). 400 path reads the body BEFORE raise_for_status() so
    Datasette's friendly error message survives (RESEARCH Pitfall 1 / threat
    T-06-02-03).
    """
    ds_params: dict[str, Any] = {"sql": sql, "_shape": "objects"}
    for name, value in (params or {}).items():
        ds_params[f"_param_{name}"] = value
    r = await client.get(f"/{db}.json", params=ds_params)
    if r.status_code == 404:
        return None, "Database not found"
    # Defensive parse — if upstream returns HTML (Caddy 502, datasette
    # error page, network MITM page) rather than JSON, surface a clean
    # error string instead of letting ValueError propagate as 500. The
    # sibling _safe_search_one in routes_search.py already catches both
    # httpx.HTTPError and ValueError; matching that contract here.
    try:
        body = r.json()
    except ValueError:
        return None, "Upstream returned a non-JSON response"
    if r.status_code == 400:
        return None, body.get("error") or "Query failed"
    r.raise_for_status()
    return body, body.get("error")

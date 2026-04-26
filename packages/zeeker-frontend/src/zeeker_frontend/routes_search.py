"""Phase 6 — GET /search: cross-database FTS UI.

Fans out per-table FTS calls via asyncio.gather(return_exceptions=True) over
app.state.searchable_tables, groups results by (db, table), renders two states.

Critical invariants (RESEARCH §Pattern 1 + Pitfalls 2 / 10):
  - Uses asyncio.gather(*tasks, return_exceptions=True). The cancel-on-first-
    failure structured-concurrency primitive (RESEARCH Pitfall 2) is forbidden
    here — one slow table would empty /search.
  - _safe_search_one converts httpx.HTTPError + ValueError to None sentinel so
    one failing table does NOT abort the whole response (RESEARCH Pitfall 2).
  - Empty-cache 503 only fires when q is non-empty (Pitfall 10). State A
    (empty q) always renders.
  - Title column is computed server-side via _pick_title_column(columns,
    primary_keys) using Datasette's declared `columns` array — NOT row.items()
    iteration order. Handler attaches row["__title__"] (pre-truncated) so the
    partial renders {{ row["__title__"] }} directly without dict-iteration
    heuristics. Robust against Python dict iteration order changes.
  - q is autoescaped by Jinja in the .html template; the handler does NOT
    sanitize / strip / regex-replace q (RESEARCH §Security Domain).
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import fetch_site_metadata


router = APIRouter()

_CACHE_HEADER = "public, max-age=60, stale-while-revalidate=300"


async def _safe_search_one(
    client: httpx.AsyncClient, db: str, table: str, q: str, size: int
) -> dict | None:
    """Single per-table FTS call. Errors converted to None (caller drops the group).

    NEVER raises — RESEARCH Pitfall 2 (one bad table must not abort the whole search).
    Catches both httpx.HTTPError (transport/HTTP errors) AND ValueError
    (json-decode errors) so any failure mode collapses to the same sentinel.
    """
    try:
        r = await client.get(
            f"/{db}/{table}.json",
            params={"_search": q, "_size": size, "_shape": "objects"},
            timeout=httpx.Timeout(3.0, connect=1.0),
        )
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError):
        return None


def _derive_pk_value(row: dict, primary_keys: list[str]) -> str | None:
    """Return the comma-joined PK value(s) for row_url; None if PK can't be derived."""
    if not primary_keys:
        return None
    parts = []
    for k in primary_keys:
        v = row.get(k)
        if v is None:
            return None
        parts.append(str(v))
    return ",".join(parts)


def _pick_title_column(columns: list[str], primary_keys: list[str]) -> str | None:
    """First non-PK column from the JSON `columns` array.

    The `columns` array preserves Datasette's declared order (verified in
    Pattern 1 response shape). Picking from this array — NOT from row.keys() —
    is robust against Python dict iteration order, JSON parser ordering, or
    future Datasette changes that might add fields to row dicts (e.g.
    _search_highlight) ahead of declared columns.
    """
    for c in columns or []:
        if c not in (primary_keys or []):
            return c
    return None


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", _retry: int = 0):
    client: httpx.AsyncClient = request.app.state.http
    searchable: dict[str, list[str]] = getattr(
        request.app.state, "searchable_tables", {}
    )

    q_stripped = q.strip()

    # Pull site metadata so base.html nav `menu_links` renders correctly
    # (precedent set by Plan 03 /about + /how-to-use; uses 60s TTL cache so
    # the cost is negligible). State A still does NOT call datasette beyond
    # this cached metadata fetch — fan-out is gated by `q_stripped`.
    site_metadata = await fetch_site_metadata(client)

    # State A — empty query: hero + tips, no fan-out, no datasette FTS calls.
    if not q_stripped:
        response = request.app.state.templates.TemplateResponse(
            request=request,
            name="pages/search.html",
            context={
                "q": "",
                "groups": [],
                "total_count": 0,
                "n_databases": 0,
                "failures": 0,
                "metadata": site_metadata,
                "page_class": "page-search",
                "breadcrumbs": [{"label": "Search"}],
                "current_year": datetime.now().year,
            },
        )
        response.headers["Cache-Control"] = _CACHE_HEADER
        return response

    # Pitfall 10 — non-empty q but no searchable tables (boot blip): friendly 503.
    if not searchable:
        raise HTTPException(
            status_code=503,
            detail="Search temporarily unavailable. Try again in a minute.",
        )

    # State B — fan out via gather(return_exceptions=True). The structured-
    # concurrency primitive that cancels siblings on first failure is
    # forbidden here (Pitfall 2 — would empty /search on one slow table).
    pairs: list[tuple[str, str]] = [
        (db, t) for db, ts in searchable.items() for t in ts
    ]
    tasks = [_safe_search_one(client, db, t, q_stripped, 10) for db, t in pairs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    groups: list[dict] = []
    failures = 0
    for (db, t), r in zip(pairs, results):
        if r is None or isinstance(r, BaseException):
            failures += 1
            continue
        rows = r.get("rows") or []
        if not rows:
            continue  # skip 0-result groups per UI-SPEC
        primary_keys = r.get("primary_keys") or []
        columns = r.get("columns") or []
        # Compute title column SERVER-SIDE from declared `columns` array
        # (NOT row.items()). Robust against dict iteration order — see
        # _pick_title_column docstring.
        title_col = _pick_title_column(columns, primary_keys)
        for row in rows:
            row["_pk_str"] = _derive_pk_value(row, primary_keys)
            # Pre-compute title so the partial renders {{ row["__title__"] }}
            # directly. Falls back to PK string or empty string.
            title_val = row.get(title_col) if title_col else None
            if isinstance(title_val, str) and title_val:
                row["__title__"] = title_val[:120]
            elif row.get("_pk_str"):
                row["__title__"] = row["_pk_str"]
            else:
                row["__title__"] = ""
        groups.append(
            {
                "db": db,
                "table": t,
                "count": r.get("filtered_table_rows_count") or len(rows),
                "rows": rows[:10],
                "primary_keys": primary_keys,
                "columns": columns,
                "title_col": title_col,
            }
        )
    groups.sort(key=lambda g: (g["db"], g["table"]))

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/search.html",
        context={
            "q": q_stripped,
            "groups": groups,
            "total_count": sum(g["count"] for g in groups),
            "n_databases": len({g["db"] for g in groups}),
            "failures": failures,
            "metadata": site_metadata,
            "page_class": "page-search",
            "breadcrumbs": [{"label": "Search"}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = _CACHE_HEADER
    return response

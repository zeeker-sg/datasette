"""GET / — home page. Phase 4 first user-visible route."""
from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import (
    fetch_databases,
    fetch_site_metadata,
    is_hidden_table,
)

router = APIRouter()


def _filter_wildcard(metadata: dict) -> dict:
    """Strip the `*` wildcard key from metadata.databases (RESEARCH Pitfall 4).

    Datasette uses `*` as a cross-cutting metadata key; it's not a real database.
    We return a shallow-copied metadata dict with the filtered `databases` sub-dict.
    """
    if not metadata:
        return {}
    dbs = metadata.get("databases") or {}
    cleaned = {k: v for k, v in dbs.items() if k != "*"}
    return {**metadata, "databases": cleaned}


def _visible_tables_count(entry: dict) -> int:
    """Visible-table count for a /.json database entry (see caller comment)."""
    tables = entry.get("tables")
    if isinstance(tables, list):
        return len([t for t in tables if not is_hidden_table(t)])
    truncated = entry.get("tables_and_views_truncated")
    if isinstance(truncated, list) and not entry.get("tables_and_views_more"):
        return len([t for t in truncated if not is_hidden_table(t)])
    return entry.get("tables_count") or 0


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    client: httpx.AsyncClient = request.app.state.http
    # Fetch the database list + site metadata in parallel for lower latency.
    # If the list fetch fails, we bail; if metadata fails, datasette_client
    # returns {} and the template uses its defensive fallbacks.
    try:
        databases = await fetch_databases(client)
    except httpx.HTTPError:
        # Datasette is sick. Serve a 503, NOT a stack-trace 500.
        raise HTTPException(status_code=503, detail="Data API unavailable")

    raw_metadata = await fetch_site_metadata(client)
    metadata = _filter_wildcard(raw_metadata)

    # Filter databases flagged hidden + any _zeeker-prefixed platform db.
    visible_dbs = [
        d for d in databases
        if not d.get("hidden") and not d.get("name", "").startswith("_zeeker")
    ]

    # Recompute per-db table counts from a filtered source rather than
    # trusting Datasette's raw tables_count blindly:
    #   - fixture/older shape: full `tables` list → recount via the shared
    #     hidden predicate (cheapest correct option, no extra requests);
    #   - live /.json shape: `tables_and_views_truncated` is capped at 5, so
    #     it's only authoritative when `tables_and_views_more` is false;
    #   - otherwise fall back to Datasette's `tables_count`, which already
    #     excludes hidden-flagged tables (site metadata marks _zeeker_*,
    #     *_fragments, etc. hidden, so the served count converges).
    for d in visible_dbs:
        d["tables_count"] = _visible_tables_count(d)

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "databases": visible_dbs,
            "stats": {"db_count": len(visible_dbs)},
            "metadata": metadata,
            "current_year": datetime.now().year,
            "breadcrumbs": None,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response

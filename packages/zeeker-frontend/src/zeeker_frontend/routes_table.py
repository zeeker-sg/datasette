"""GET /{db}/{table} — table browse page (Phase 5; catalogue posture).

LIST-ALWAYS: tables render feed mode (or longform-list when display says so).
There is no tabular mode — the site is a catalogue of summaries, identifying
data, and source links; raw column grids (and full-text columns) never render.
Display slots are computed SERVER-SIDE via compute_display_slots, which
excludes primary keys and protected columns from every slot.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import (
    compute_display_slots,
    fetch_site_metadata,
    fetch_table,
    is_hidden_table_name,
    protected_columns,
)

router = APIRouter()


def _db_title(site_metadata: dict, db: str) -> str:
    entry = (site_metadata.get("databases") or {}).get(db) or {}
    return entry.get("title") or db.replace("-", " ").replace("_", " ").title()


@router.get("/{db}/{table}", response_class=HTMLResponse)
async def table_page(request: Request, db: str, table: str):
    # Hidden-table guard — same wording for missing vs. hidden (no info
    # disclosure). Uses the shared name predicate (_zeeker*, *_fts*,
    # *_fragments).
    if is_hidden_table_name(table):
        raise HTTPException(status_code=404, detail="Table not found")

    client: httpx.AsyncClient = request.app.state.http

    # fetch_table internally allowlists query params + forces _shape=objects.
    try:
        payload = await fetch_table(client, db, table, dict(request.query_params))
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Data API unavailable")

    if payload is None:
        raise HTTPException(status_code=404, detail="Table not found")

    site_metadata = await fetch_site_metadata(client)
    db_entry = (site_metadata.get("databases") or {}).get(db) or {}
    table_meta = (db_entry.get("tables") or {}).get(table) or {}
    display = table_meta.get("display") or {}

    # LIST-ALWAYS — feed unless display explicitly opts into longform-list.
    table_mode = "longform-list" if display.get("table_mode") == "longform-list" else "feed"
    row_mode = display.get("row_mode") or "tabular"

    rows = payload.get("rows") or []
    columns = payload.get("columns") or []
    primary_keys = payload.get("primary_keys") or []

    # Protected (full-text) columns — from site metadata plugins.strip-columns.
    # These can never occupy a display slot and gate the CSV export link
    # (Datasette 403s .csv for protected tables).
    protected = protected_columns(site_metadata, db, table, columns)
    display_columns = compute_display_slots(
        columns, rows, primary_keys, protected,
        table_meta=table_meta,
        overrides=display.get("columns") or {},
    )

    # Pitfall 2 — datasette next_url is fully-qualified to internal hostname
    # and points to .json. Strip host + path; reuse only the querystring.
    next_url = None
    ds_next = payload.get("next_url")
    if ds_next:
        parsed = urlparse(ds_next)
        if parsed.query:
            next_url = f"/{db}/{table}?{parsed.query}"

    # Applied facet/column filters — anything that's a plain column name in the
    # query string. Used by applied_facets.html for the .filter-chip row.
    applied_filters = [
        (k, v) for k, v in request.query_params.multi_items()
        if not k.startswith("_")
    ]

    # Active FTS term — surfaced as a removable chip + drives "No results" copy.
    active_search = request.query_params.get("_search") or ""

    merged_metadata = {
        "title": db_entry.get("title"),
        "description": db_entry.get("description"),
        "source": payload.get("source"),
        "source_url": payload.get("source_url"),
        "license": payload.get("license"),
        "license_url": payload.get("license_url"),
        "tables": db_entry.get("tables", {}),
        "menu_links": site_metadata.get("menu_links", []),
    }

    breadcrumb_db = _db_title(site_metadata, db)
    breadcrumb_table = table_meta.get("title") or table.replace("_", " ").replace("-", " ").title()

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="table.html",
        context={
            "database": db,
            "table": table,
            "rows": rows,
            "columns": columns,
            "primary_keys": primary_keys,
            "facet_results": payload.get("facet_results") or {},
            "suggested_facets": payload.get("suggested_facets") or [],
            "filtered_table_rows_count": payload.get("filtered_table_rows_count"),
            "next_url": next_url,
            "request_qs": request.url.query,
            "table_mode": table_mode,
            "row_mode": row_mode,
            "display": display,
            "display_columns": display_columns,
            "is_protected_table": bool(protected),
            "table_meta": table_meta,
            "metadata": merged_metadata,
            "breadcrumbs": [
                {"href": f"/{db}", "label": breadcrumb_db},
                {"label": breadcrumb_table},
            ],
            "breadcrumb_table": breadcrumb_table,
            "current_year": datetime.now().year,
            "applied_filters": applied_filters,
            "active_search": active_search,
            "human_description_en": payload.get("human_description_en"),
            "is_view": payload.get("is_view", False),
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response

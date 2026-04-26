"""GET /{db}/{table} — table browse page (Phase 5)."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import fetch_table, fetch_site_metadata

router = APIRouter()

# T-05-03 mitigation — both prefix AND suffix per RESEARCH Pitfall 6.
_HIDDEN_TABLE_PREFIXES = ("_zeeker",)
_HIDDEN_TABLE_SUFFIXES = (
    "_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config",
)


def _db_title(site_metadata: dict, db: str) -> str:
    entry = (site_metadata.get("databases") or {}).get(db) or {}
    return entry.get("title") or db.replace("-", " ").replace("_", " ").title()


@router.get("/{db}/{table}", response_class=HTMLResponse)
async def table_page(request: Request, db: str, table: str):
    # Hidden-table guard — same wording for missing vs. hidden (no info disclosure).
    if table.startswith(_HIDDEN_TABLE_PREFIXES) or table.endswith(_HIDDEN_TABLE_SUFFIXES):
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

    # D-04 — tabular fallback when no display hint set.
    table_mode = display.get("table_mode") or "tabular"
    row_mode = display.get("row_mode") or "tabular"

    # Pitfall 2 — datasette next_url is fully-qualified to internal hostname
    # and points to .json. Strip host + path; reuse only the querystring.
    next_url = None
    ds_next = payload.get("next_url")
    if ds_next:
        parsed = urlparse(ds_next)
        if parsed.query:
            next_url = f"/{db}/{table}?{parsed.query}"

    # Sort state for column-header cycling in tabular mode.
    qp = dict(request.query_params)
    if qp.get("_sort"):
        current_sort_dir, current_sort_col = "asc", qp["_sort"]
    elif qp.get("_sort_desc"):
        current_sort_dir, current_sort_col = "desc", qp["_sort_desc"]
    else:
        current_sort_dir, current_sort_col = None, None

    # Applied facet/column filters — anything that's a plain column name in the
    # query string. Used by applied_facets.html for the .filter-chip row.
    applied_filters = [
        (k, v) for k, v in request.query_params.multi_items()
        if not k.startswith("_")
    ]

    # Active FTS term — surfaced as a removable chip + drives "No results" copy.
    active_search = qp.get("_search") or ""

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
            "rows": payload.get("rows") or [],
            "columns": payload.get("columns") or [],
            "primary_keys": payload.get("primary_keys") or [],
            "facet_results": payload.get("facet_results") or {},
            "suggested_facets": payload.get("suggested_facets") or [],
            "filtered_table_rows_count": payload.get("filtered_table_rows_count"),
            "next_url": next_url,
            "request_qs": request.url.query,
            "table_mode": table_mode,
            "row_mode": row_mode,
            "display": display,
            "display_columns": display.get("columns") or {},
            "table_meta": table_meta,
            "metadata": merged_metadata,
            "breadcrumbs": [
                {"href": f"/{db}", "label": breadcrumb_db},
                {"label": breadcrumb_table},
            ],
            "breadcrumb_table": breadcrumb_table,
            "current_year": datetime.now().year,
            "current_sort_col": current_sort_col,
            "current_sort_dir": current_sort_dir,
            "applied_filters": applied_filters,
            "active_search": active_search,
            "human_description_en": payload.get("human_description_en"),
            "is_view": payload.get("is_view", False),
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response

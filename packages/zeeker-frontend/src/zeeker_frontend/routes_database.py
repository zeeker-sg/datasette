"""GET /{db} — database overview page. Phase 4."""
from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import fetch_database, fetch_site_metadata

router = APIRouter()


@router.get("/{db}", response_class=HTMLResponse)
async def database(request: Request, db: str):
    client: httpx.AsyncClient = request.app.state.http

    # Pitfall 1: fetch_database returns None on 404; raises on other errors.
    try:
        payload = await fetch_database(client, db)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Data API unavailable")

    if payload is None:
        # Pitfall 1 revisited: explicit 404 — NOT a generic 500 traceback.
        raise HTTPException(status_code=404, detail="Database not found")

    # Pitfall 5: trust Datasette's `hidden: true` flag. It covers BOTH
    # `_zeeker_*` metadata tables AND FTS internals (*_fts, *_fts_data,
    # *_fts_docsize, *_fts_idx). Do NOT prefix-check — it misses FTS.
    visible_tables = [t for t in payload.get("tables", []) if not t.get("hidden")]

    # Per-DB title/description live in /-/metadata.json.databases[db]. Source/license
    # are already merged into /{db}.json top-level by datasette — pass both up.
    site_metadata = await fetch_site_metadata(client)
    db_entry = (site_metadata.get("databases") or {}).get(db) or {}
    merged_metadata = {
        "title": db_entry.get("title"),
        "description": db_entry.get("description"),
        "source": payload.get("source"),
        "source_url": payload.get("source_url"),
        "license": payload.get("license"),
        "license_url": payload.get("license_url"),
        # Nested tables metadata for per-table friendly titles/descriptions
        "tables": db_entry.get("tables", {}),
        # Preserve menu_links so base.html nav renders correctly
        "menu_links": site_metadata.get("menu_links", []),
    }

    breadcrumb_label = merged_metadata["title"] or db.replace("-", " ").replace("_", " ").title()

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="database.html",
        context={
            "database": db,
            "tables": visible_tables,
            "views": payload.get("views", []),
            "canned_queries": payload.get("queries", []),
            "size": payload.get("size"),
            "metadata": merged_metadata,
            "breadcrumbs": [{"label": breadcrumb_label}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response

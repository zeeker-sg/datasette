"""GET /{db}/{table}/{pk} — single row view (Phase 5)."""
from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import (
    fetch_row,
    fetch_site_metadata,
    is_hidden_table,
)
from zeeker_frontend.routes_table import _detect_feed_columns

router = APIRouter()

_PK_DISPLAY_MAX = 12  # UI-SPEC §Always-present chrome — truncate UUID/hash PKs in breadcrumb


def _db_title(site_metadata: dict, db: str) -> str:
    entry = (site_metadata.get("databases") or {}).get(db) or {}
    return entry.get("title") or db.replace("-", " ").replace("_", " ").title()


def _truncate_pk(pk: str, n: int = _PK_DISPLAY_MAX) -> str:
    if len(pk) <= n:
        return pk
    return pk[:n] + "…"


@router.get("/{db}/{table}/{pk}", response_class=HTMLResponse)
async def row_page(request: Request, db: str, table: str, pk: str):
    # Hidden-table guard — same wording for missing vs. hidden.
    if is_hidden_table(table):
        raise HTTPException(status_code=404, detail="Table not found")

    client: httpx.AsyncClient = request.app.state.http

    try:
        payload = await fetch_row(client, db, table, pk)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Data API unavailable")

    if payload is None:
        raise HTTPException(status_code=404, detail="Record not found")

    # Single-row endpoint returns rows: [single_dict]; defensive guard if empty.
    rows = payload.get("rows") or []
    if not rows:
        raise HTTPException(status_code=404, detail="Record not found")
    row = rows[0]

    site_metadata = await fetch_site_metadata(client)
    db_entry = (site_metadata.get("databases") or {}).get(db) or {}
    table_meta = (db_entry.get("tables") or {}).get(table) or {}
    display = table_meta.get("display") or {}
    display_columns = display.get("columns") or {}

    # Feed-by-convention: if no explicit display.columns set, auto-detect
    # from column names so the row page can use the article layout without
    # a metadata hint.
    if not display_columns:
        detected = _detect_feed_columns(payload.get("columns") or [])
        if detected:
            display_columns = detected

    # D-04 — tabular fallback when no display.row_mode set.
    # If the table matched the feed convention and no explicit row_mode
    # was set, default to "article" so the row page matches the feed.
    row_mode = display.get("row_mode")
    if not row_mode:
        row_mode = "article" if display_columns else "tabular"

    # Page H1 — slot-driven if display.columns.title is set; else generic "Record".
    title_col = display_columns.get("title")
    page_title = (row.get(title_col) if title_col else None) or "Record"

    # Long-text precomputation — for tabular mode <details> wrapping.
    long_text_columns = {
        col: (isinstance(row.get(col), str) and len(row.get(col, "")) > 200)
        for col in (payload.get("columns") or [])
    }

    merged_metadata = {
        "title": db_entry.get("title"),
        "description": db_entry.get("description"),
        "tables": db_entry.get("tables", {}),
        "menu_links": site_metadata.get("menu_links", []),
    }

    breadcrumb_db = _db_title(site_metadata, db)
    breadcrumb_table = table_meta.get("title") or table.replace("_", " ").replace("-", " ").title()
    pk_label = _truncate_pk(pk)

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="row.html",
        context={
            "database": db,
            "table": table,
            "pk": pk,
            "pk_label": pk_label,
            "row": row,
            "columns": payload.get("columns") or [],
            "primary_keys": payload.get("primary_keys") or [],
            "primary_key_values": payload.get("primary_key_values") or [],
            "row_mode": row_mode,
            "display": display,
            "display_columns": display_columns,
            "table_meta": table_meta,
            "metadata": merged_metadata,
            "page_title": page_title,
            "long_text_columns": long_text_columns,
            "breadcrumbs": [
                {"href": f"/{db}", "label": breadcrumb_db},
                {"href": f"/{db}/{table}", "label": breadcrumb_table},
                {"label": pk_label},
            ],
            "breadcrumb_table": breadcrumb_table,
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response

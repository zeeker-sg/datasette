"""GET /{db}/{table}/{pk} — single row view (Phase 5; catalogue posture).

Uniform catalogue rule: a protected (full-text) column's value is NEVER
rendered — not in the body slot, not in the aside, not behind a <details>.
Slots are computed server-side with the same heuristic as the table page;
the aside lists only columns that are not protected AND whose value is
< 200 chars.
"""
from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import (
    compute_display_slots,
    fetch_row,
    fetch_site_metadata,
    is_hidden_table_name,
    protected_columns,
    safe_aside_columns,
)

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
    if is_hidden_table_name(table):
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

    columns = payload.get("columns") or []
    primary_keys = payload.get("primary_keys") or []

    # Protected columns + server-side slot computation (same heuristic as
    # the table page; protected columns are excluded from every slot).
    protected = protected_columns(site_metadata, db, table, columns)
    display_columns = compute_display_slots(
        columns, [row], primary_keys, protected,
        table_meta=table_meta,
        overrides=display.get("columns") or {},
    )

    # D-04 — generic catalogue-record fallback when no display.row_mode set.
    row_mode = display.get("row_mode") or "tabular"

    # Page H1 — slot-driven; "Record" is the last-ditch fallback.
    title_col = display_columns.get("title")
    page_title = (row.get(title_col) if title_col else None) or "Record"

    # Aside: only short, non-protected values; mapped title/body excluded
    # to avoid duplicating the main reading column.
    aside_columns = safe_aside_columns(
        columns, row, protected,
        exclude={c for c in (display_columns.get("title"), display_columns.get("body")) if c},
    )

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
            "columns": columns,
            "primary_keys": primary_keys,
            "primary_key_values": payload.get("primary_key_values") or [],
            "row_mode": row_mode,
            "display": display,
            "display_columns": display_columns,
            "aside_columns": aside_columns,
            "is_protected_table": bool(protected),
            "table_meta": table_meta,
            "metadata": merged_metadata,
            "page_title": page_title,
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

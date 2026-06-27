"""GET /{db} — database overview page. Phase 4; catalogue posture.

Listing surfaces (tables, views, canned queries) are all filtered through the
shared hidden predicate in datasette_client.is_hidden_table — Datasette's
hidden/private flags plus the name rules (_zeeker*, *_fts*, *_fragments).
"""
from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import (
    fetch_database,
    fetch_site_metadata,
    is_hidden_table,
    is_protected_table,
)

router = APIRouter()


def _normalize_named(items) -> list[dict]:
    """Normalize views/queries payloads to a list of dicts with `name`.

    Live Datasette 0.65 serves both as lists (of dicts or strings); older
    captures show `queries` as a dict keyed by name. Handle all three.
    """
    if not items:
        return []
    if isinstance(items, dict):
        items = [
            {"name": k, **(v if isinstance(v, dict) else {})}
            for k, v in items.items()
        ]
    out: list[dict] = []
    for item in items:
        if isinstance(item, str):
            item = {"name": item}
        out.append(item)
    return out


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

    # Shared hidden predicate — covers Datasette's hidden flag AND the
    # name rules (_zeeker* platform tables, *_fts* shadows, *_fragments
    # chunk tables). Applied to tables, views AND canned queries.
    visible_tables = [
        t for t in payload.get("tables", []) if not is_hidden_table(t)
    ]
    views = [
        v for v in _normalize_named(payload.get("views")) if not is_hidden_table(v)
    ]
    canned_queries = []
    for q in _normalize_named(payload.get("queries")):
        if is_hidden_table(q):
            continue
        q.setdefault("title", q.get("name"))
        canned_queries.append(q)

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

    # Protected tables (strip-columns) — their .csv export 403s, so the
    # template renders the JSON link only.
    protected_table_names = {
        t.get("name")
        for t in visible_tables
        if is_protected_table(
            site_metadata, db, t.get("name", ""),
            # /{db}.json table dicts carry the column list (verified live);
            # guard against shapes where `columns` is a count.
            t.get("columns") if isinstance(t.get("columns"), list) else None,
        )
    }

    breadcrumb_label = merged_metadata["title"] or db.replace("-", " ").replace("_", " ").title()

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="database.html",
        context={
            "database": db,
            "tables": visible_tables,
            "views": views,
            "canned_queries": canned_queries,
            "protected_tables": protected_table_names,
            "size": payload.get("size"),
            "metadata": merged_metadata,
            "breadcrumbs": [{"label": breadcrumb_label}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response

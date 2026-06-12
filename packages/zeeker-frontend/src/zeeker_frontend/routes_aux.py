"""Phase 6 — auxiliary HTML routes ported 1:1 from M1 plugins.

Routes: /developers, /status, /sources, /about, /how-to-use, /llms.txt, /robots.txt
All GET, all autonomous, all read-only via httpx through app.state.http.

Patterns established by Plan 06-03:
  - Each handler sets `Cache-Control: public, max-age=60, stale-while-revalidate=300`
    (D-14) — except /robots.txt (static file, served as-is).
  - Each HTML handler passes `page_class="page-{slug}"` so base.html can scope
    Phase-6 CSS subsections without leaking into Phase 4-5 surfaces.
  - Hidden-table dual predicate (D-15) — `_hidden(t)` filters BOTH `hidden=True`
    flag (covers FTS internals like *_fts) AND `_zeeker_*` prefix (platform tables
    that may have hidden=False in some overlays). RESEARCH §Pitfall 4.
  - Upstream errors → `HTTPException(503)` (mirror routes_database.py:21-27 pattern).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from zeeker_frontend.datasette_client import (
    fetch_database,
    fetch_databases,
    fetch_site_metadata,
    is_hidden_table,
)

router = APIRouter()

_STATIC_DIR = Path(__file__).parent / "static"

# Catalogue posture — protected full-text column names that must never be
# enumerated on /developers or /llms.txt. The single source of truth is the
# plugins.strip-columns block in repo-root metadata.json (served via
# /-/metadata.json); this constant is a defensive fallback for deployments
# where that block has not propagated yet.
_FALLBACK_DENY_NAMES = ("content_text", "full_text", "html_raw", "footnote_text")


def _hidden(t: dict) -> bool:
    """Hidden-from-listings predicate (catalogue posture).

    Delegates to the canonical shared predicate in datasette_client
    (hidden/private flag OR _zeeker prefix OR *_fts* shadow OR *_fragments).
    """
    return is_hidden_table(t)


def _protected_columns(site_metadata: dict, db: str, table: str) -> set[str]:
    """Protected column names for (db, table) per the strip-columns contract.

    A column is protected if its name is in default_deny_names OR listed for
    its (db, table) in plugins.strip-columns.tables. Falls back to the
    hardcoded deny names when the metadata block is absent.
    """
    cfg = (site_metadata.get("plugins") or {}).get("strip-columns") or {}
    deny = set(cfg.get("default_deny_names") or _FALLBACK_DENY_NAMES)
    per_table = ((cfg.get("tables") or {}).get(db) or {}).get(table) or []
    return deny | set(per_table)


def _strip_protected(site_metadata: dict, db: str, table: dict) -> dict:
    """Return a copy of the table dict with protected column names removed
    from its `columns` list. Never mutates the upstream payload."""
    protected = _protected_columns(site_metadata, db, table.get("name", ""))
    return {
        **table,
        "columns": [c for c in (table.get("columns") or []) if c not in protected],
    }


async def _collect_db_blocks(client: httpx.AsyncClient) -> list[dict]:
    """Iterate /-/databases.json + /{db}.json. Used by /sources, /developers, /llms.txt.

    Returns: list of {name, title, description, source_url, license, license_url, size,
                      tables: [filtered table dicts]} per database.

    Table dicts have protected full-text column names stripped from their
    `columns` lists (catalogue posture — protected columns are never
    enumerated in docs surfaces).

    Raises HTTPException(503) on upstream connection failure (database listing).
    Per-database fetch errors are tolerated (skip that database).
    """
    try:
        dbs = await fetch_databases(client)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")

    site_metadata = await fetch_site_metadata(client)

    blocks: list[dict] = []
    for entry in dbs:
        name = entry.get("name")
        if not name:
            continue
        try:
            payload = await fetch_database(client, name)
        except httpx.HTTPError:
            continue
        if payload is None:
            continue
        tables = [
            _strip_protected(site_metadata, name, t)
            for t in (payload.get("tables") or [])
            if not _hidden(t)
        ]
        db_meta = (site_metadata.get("databases") or {}).get(name) or {}
        blocks.append({
            "name": name,
            "title": db_meta.get("title") or name,
            "description": db_meta.get("description") or payload.get("description") or "",
            "source_url": db_meta.get("source_url") or payload.get("source_url") or "",
            "license": db_meta.get("license") or payload.get("license") or "",
            "license_url": db_meta.get("license_url") or payload.get("license_url") or "",
            "size": entry.get("size"),
            "tables": tables,
            "table_count": len(tables),
        })
    return blocks


@router.get("/developers", response_class=HTMLResponse)
async def developers(request: Request):
    client: httpx.AsyncClient = request.app.state.http
    db_blocks = await _collect_db_blocks(client)
    site_metadata = await fetch_site_metadata(client)
    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/developers.html",
        context={
            "databases": db_blocks,
            "metadata": site_metadata,
            "page_class": "page-developers",
            "breadcrumbs": [{"label": "Developers"}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


@router.get("/status", response_class=HTMLResponse)
async def status(request: Request):
    client: httpx.AsyncClient = request.app.state.http
    try:
        dbs = await fetch_databases(client)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")

    total_databases = len(dbs)
    total_tables = 0
    total_rows = 0
    for entry in dbs:
        name = entry.get("name")
        if not name:
            continue
        try:
            payload = await fetch_database(client, name)
        except httpx.HTTPError:
            continue
        if payload is None:
            continue
        for t in payload.get("tables") or []:
            if _hidden(t):
                continue
            total_tables += 1
            total_rows += int(t.get("count") or 0)

    site_metadata = await fetch_site_metadata(client)

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/status.html",
        context={
            "system_stats": {
                "total_databases": total_databases,
                "total_tables": total_tables,
                "total_rows": total_rows,
            },
            "recent_updates": getattr(request.app.state, "changelog", []),
            "metadata": site_metadata,
            "page_class": "page-status",
            "breadcrumbs": [{"label": "Status"}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


@router.get("/sources", response_class=HTMLResponse)
async def sources(request: Request):
    client: httpx.AsyncClient = request.app.state.http
    db_blocks = await _collect_db_blocks(client)
    site_metadata = await fetch_site_metadata(client)
    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/sources.html",
        context={
            "databases": db_blocks,
            "metadata": site_metadata,
            "page_class": "page-sources",
            "breadcrumbs": [{"label": "Sources"}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    # /about does not call datasette — it's static prose. We still pull
    # site_metadata for the nav menu_links (base.html iterates them).
    client: httpx.AsyncClient = request.app.state.http
    site_metadata = await fetch_site_metadata(client)
    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/about.html",
        context={
            "metadata": site_metadata,
            "page_class": "page-about",
            "breadcrumbs": [{"label": "About"}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


@router.get("/how-to-use", response_class=HTMLResponse)
async def how_to_use(request: Request):
    # /how-to-use does not call datasette — static guide. Same pattern as /about.
    client: httpx.AsyncClient = request.app.state.http
    site_metadata = await fetch_site_metadata(client)
    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/how_to_use.html",
        context={
            "metadata": site_metadata,
            "page_class": "page-how-to-use",
            "breadcrumbs": [{"label": "How to use"}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt(request: Request):
    """Plain-text machine-readable description.

    Body shape mirrors plugins/developers_page.py lines 81-121.
    Uses templates.get_template (NOT TemplateResponse) because the MIME type
    differs and Jinja autoescape is OFF for `.txt` files (RESEARCH Pitfall 8).
    """
    client: httpx.AsyncClient = request.app.state.http
    db_blocks = await _collect_db_blocks(client)
    body = request.app.state.templates.get_template("llms.txt").render(
        databases=db_blocks,
    )
    response = PlainTextResponse(content=body, media_type="text/plain; charset=utf-8")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Verbatim file from static/robots.txt (RESEARCH Pitfall 13).

    Single FileResponse-style handler so the URL is `/robots.txt` (not
    `/static/robots.txt`); avoids dead-code path created by mounting the
    static dir AND adding a route handler (Pitfall 13).
    """
    return PlainTextResponse(
        content=(_STATIC_DIR / "robots.txt").read_text(encoding="utf-8"),
        media_type="text/plain; charset=utf-8",
    )


# --- /sql removal (catalogue posture) -----------------------------------
# The in-browser SQL editor was removed entirely. Stale bookmarks/links to
# /sql and /sql/{db} permanently redirect to the developer docs instead of
# 404ing. These routes register via aux_router, which main.py includes
# BEFORE database_router, so /sql never falls through to the /{db} catch-all.


@router.get("/sql")
async def sql_redirect():
    return RedirectResponse(url="/developers", status_code=301)


@router.get("/sql/{db}")
async def sql_db_redirect(db: str):
    return RedirectResponse(url="/developers", status_code=301)

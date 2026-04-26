"""Phase 6 — /sql route family: landing list + per-database editor.

GET /sql        → list of databases (link-out to /sql/{db})
GET /sql/{db}   → empty editor (or pre-filled if ?sql=… provided); does NOT execute
POST /sql/{db}  → execute SQL via datasette_client.execute_sql; render results/error

Critical invariants (RESEARCH §Pattern 4 + §Pitfall 1 + §Pitfall 7):
  - POST builds upstream params via EXPLICIT allowlist: only `sql` + detected
    `:param` names (validated via _PARAM_RE) reach datasette via execute_sql.
    Everything else in `request.form()` is silently dropped — closes the
    SSRF-ish querystring-smuggling surface (threat T-06-05-02).
  - Param values are bound via Datasette's `_param_<name>` URL keys (handled
    inside execute_sql) — NEVER concatenated into the SQL string. The regex
    `[a-zA-Z_][a-zA-Z0-9_]*` restricts param names so a malicious form field
    name can't smuggle a different datasette param (threat T-06-05-01).
  - 400-error path: execute_sql returns (None, error_string); handler renders
    the friendly error inline (HTTP 200 with .sql-error block) — does NOT 503
    (threat T-06-05-03 / RESEARCH Pitfall 1).
  - Cache-Control: GET = `public, max-age=60, stale-while-revalidate=300`;
    POST = `no-store` (D-14 / threat T-06-05-06).
  - fetch_site_metadata is called on every handler so base.html nav menu_links
    render correctly (precedent: Plan 03 /about + /how-to-use, Plan 04 /search).
"""
from __future__ import annotations

import re
from datetime import datetime

import httpx
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import (
    execute_sql,
    fetch_database,
    fetch_databases,
    fetch_site_metadata,
)


router = APIRouter()

_CACHE_HEADER = "public, max-age=60, stale-while-revalidate=300"

# RESEARCH §Pattern 4 — :param_name detection in SQL string. Restricts param
# names to identifier syntax so a malicious form field name can never be used
# to smuggle a non-_param_<name> datasette key (threat T-06-05-01 / T-06-05-02).
_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


def _detect_params(sql: str) -> list[str]:
    """Return param names in :name encounter order, deduped.

    Used both to render param input boxes on GET (when SQL is pre-filled) and
    to gate which `_sql_param_<name>` form fields are allowed through to the
    upstream `_param_<name>` binding on POST.
    """
    seen: set[str] = set()
    out: list[str] = []
    for m in _PARAM_RE.finditer(sql or ""):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _hidden_db(entry: dict) -> bool:
    """Hide _zeeker_* dbs and any flagged hidden:true at db level (D-15)."""
    if entry.get("hidden"):
        return True
    name = entry.get("name", "")
    return name.startswith("_zeeker")


def _get_canned_queries(site_metadata: dict, db: str) -> dict[str, dict]:
    """Defensive accessor for metadata.databases.{db}.queries (RESEARCH §Code Examples)."""
    return ((site_metadata.get("databases") or {}).get(db) or {}).get("queries") or {}


@router.get("/sql", response_class=HTMLResponse)
async def sql_landing(request: Request):
    """GET /sql — landing page listing every visible database."""
    client: httpx.AsyncClient = request.app.state.http
    try:
        dbs = await fetch_databases(client)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")

    visible = [d for d in dbs if not _hidden_db(d)]
    site_metadata = await fetch_site_metadata(client)

    # Decorate with title + table count for editorial-row rendering. Per-db
    # /{db}.json calls run sequentially — boot-time only is the fast path
    # (Caddy + browser cache the 60s response), and parallelising adds noise
    # for a 2-3 db deployment.
    decorated: list[dict] = []
    for entry in visible:
        name = entry["name"]
        db_meta = (site_metadata.get("databases") or {}).get(name) or {}
        try:
            payload = await fetch_database(client, name)
        except httpx.HTTPError:
            payload = None
        tables_count = 0
        if payload:
            tables_count = sum(
                1 for t in (payload.get("tables") or [])
                if not (t.get("hidden") or t.get("name", "").startswith("_zeeker"))
            )
        decorated.append({
            "name": name,
            "title": db_meta.get("title") or name,
            "size": entry.get("size"),
            "tables_count": tables_count,
        })

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/sql_landing.html",
        context={
            "databases": decorated,
            "metadata": site_metadata,
            "page_class": "page-sql",
            "breadcrumbs": [{"label": "SQL"}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = _CACHE_HEADER
    return response


@router.get("/sql/{db}", response_class=HTMLResponse)
async def sql_db_get(request: Request, db: str):
    """GET /sql/{db} — render the editor with optional ?sql=… pre-fill.

    Does NOT execute the SQL on GET. The pre-fill is for shareable URLs only.
    """
    client: httpx.AsyncClient = request.app.state.http
    try:
        payload = await fetch_database(client, db)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")
    if payload is None:
        raise HTTPException(404, "Database not found")

    site_metadata = await fetch_site_metadata(client)
    canned = _get_canned_queries(site_metadata, db)
    db_meta = (site_metadata.get("databases") or {}).get(db) or {}

    # Optional pre-fill from ?sql=…  (UI-SPEC §Open Questions Q1)
    sql = request.query_params.get("sql") or ""

    # First visible table for default placeholder text
    first_table = ""
    for t in payload.get("tables") or []:
        if t.get("hidden") or t.get("name", "").startswith("_zeeker"):
            continue
        first_table = t.get("name") or ""
        break

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/sql_db.html",
        context={
            "database": db,
            "db_title": db_meta.get("title") or db,
            "sql": sql,
            "results": None,
            "error": None,
            "canned": canned,
            "detected_params": _detect_params(sql),
            "first_table": first_table,
            "metadata": site_metadata,
            "page_class": "page-sql-db",
            "breadcrumbs": [{"label": "SQL", "href": "/sql"}, {"label": db}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = _CACHE_HEADER
    return response


@router.post("/sql/{db}", response_class=HTMLResponse)
async def sql_db_post(request: Request, db: str, sql: str = Form(...)):
    """POST /sql/{db} — execute the submitted SQL and render results/error.

    Pitfall 7 — querystring allowlist. Only `_sql_param_<name>` form keys
    whose <name> matches the regex AND appears in _detect_params(sql) reach
    upstream. Everything else in request.form() is silently dropped. NEVER
    `params=request.form()`.
    """
    client: httpx.AsyncClient = request.app.state.http

    form = await request.form()
    raw_param_values: dict[str, str] = {}
    for k, v in form.items():
        if not isinstance(k, str):
            continue
        if not k.startswith("_sql_param_"):
            continue
        name = k.removeprefix("_sql_param_")
        # Validate name shape — guards against names like "id&extra=evil"
        # smuggled via the form key (regex enforces identifier syntax).
        if _PARAM_RE.fullmatch(":" + name) is None:
            continue
        raw_param_values[name] = str(v)

    detected = _detect_params(sql)
    # Only forward values for params actually mentioned in the SQL string.
    bound: dict[str, str] = {n: raw_param_values[n] for n in detected if n in raw_param_values}

    try:
        body, error = await execute_sql(client, db, sql, bound)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")

    if body is None and error == "Database not found":
        raise HTTPException(404, "Database not found")

    site_metadata = await fetch_site_metadata(client)
    canned = _get_canned_queries(site_metadata, db)
    db_meta = (site_metadata.get("databases") or {}).get(db) or {}

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/sql_db.html",
        context={
            "database": db,
            "db_title": db_meta.get("title") or db,
            "sql": sql,
            "results": body,        # dict {rows, columns, truncated, query_ms} on success; else None
            "error": error,         # str on 400-error path; None on success
            "canned": canned,
            "detected_params": detected,
            "first_table": "",
            "metadata": site_metadata,
            "page_class": "page-sql-db",
            "breadcrumbs": [{"label": "SQL", "href": "/sql"}, {"label": db}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "no-store"  # D-14
    return response

# Phase 6: Port auxiliary pages — Research

**Researched:** 2026-04-25
**Domain:** FastAPI/Jinja port of M1 Datasette plugin pages + two NEW user-facing surfaces (`/search`, `/sql`) that fan out to Datasette over internal HTTP.
**Confidence:** HIGH

## Summary

Phase 6 ports six 1:1 M1 plugin pages (`/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`) and authors two NEW surfaces (`/search`, `/sql/{db}`) into the FastAPI/Jinja frontend. The architectural pattern is locked by Phase 4 + 5: lifespan-scoped `httpx.AsyncClient`, hidden-table predicate, querystring allowlist, `Cache-Control: public, max-age=60, stale-while-revalidate=300` on every GET. Phase 6 adds two new mechanics — a one-shot FTS-discovery probe at startup (cached on `app.state.searchable_tables` for the process lifetime) and a `POST /sql/{db}` form handler that proxies through `httpx.GET /{db}.json?sql=…` to Datasette and renders results inline.

Every important Datasette response shape has been verified against the **live container** (not training data): `/-/databases.json` is a list of `{name, path, size, is_mutable, hash}` dicts; `/{db}.json` returns top-level `{tables, queries, source, license, …}` with each table carrying a load-bearing `fts_table` field that is non-null exactly when the table has an FTS counterpart; `/{db}.json?sql=…` returns `{ok, rows, truncated, columns, query, error, query_ms, …}` and — critically — **errors come back as HTTP 400 with a populated `error` field, not HTTP 200 with error**. This breaks the naive "always `raise_for_status()`" pattern; the SQL handler must inspect the body on 400 to render the friendly error block.

`datasette-search-all` (v1.1.4, confirmed loaded on the live container) emits HTML only; `/-/search.json?q=…` returns 200 with `Content-Type: text/html` — D-03 is correct that we must fan out to per-table `/{db}/{table}.json?_search=…` ourselves.

**Primary recommendation:** Build one new module per concern (`routes_aux.py` for the six 1:1 ports, `routes_search.py` for `/search`, `routes_sql.py` for `/sql` + `/sql/{db}`), extend `datasette_client.py` with `discover_searchable_tables`, `search_table`, `execute_sql`, register the three routers BEFORE `database_router` and `routes_table_router` in `main.py`, and use `asyncio.gather(..., return_exceptions=True)` (not `TaskGroup`) for `/search` fan-out so a single failed table does not abort the whole request.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `/developers`, `/status`, `/sources`, `/about`, `/how-to-use` HTML | Frontend Server (FastAPI/Jinja) | API (Datasette JSON, read-only) | Phase 4-5 pattern: HTML rendered by frontend, data via httpx; D-11 |
| `/llms.txt` text/plain | Frontend Server | API (Datasette JSON) | Same data sources as `/developers`; only the renderer changes (D-13) |
| `/search?q=` cross-database FTS | Frontend Server (fan-out + UI) | API (per-table FTS execution) | D-03; Datasette owns each FTS engine, frontend orchestrates |
| FTS-table discovery cache | Frontend Server (lifespan boot) | API (one-shot probe) | D-04: discovery is process-scoped state, not request-scoped |
| `/sql` landing + `/sql/{db}` editor | Frontend Server (form + render) | API (read-only execution) | PRD R2 v1; Datasette enforces 3s ms_limit + 1000-row cap (D-08) |
| CSV/JSON export from `/sql/{db}` results | CDN/Caddy → API | — | D-08 reuses Phase 5 D-05 suffix-routing pattern; bypasses frontend entirely |
| Static `/robots.txt` + `/favicon.ico` | Frontend Server (StaticFiles) | — | Trivial; ships under `/static/` mount or via dedicated FileResponse |
| Recent-updates timeline data | Frontend Server (boot-loaded YAML) | — | D-12: changelog ≠ daily refresh, owns its data file |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-frontend-route-set (auxiliary leg) | Frontend serves `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/search`, `/sql`, `/sql/{db}` (and `/robots.txt`); each returns 200 with rendered HTML for at least one valid input | Verifier section §M flips Phase-5's "expect 404" sentinels to "expect 200"; structural asserts confirm italic-accent H1 + `/static/css/zeeker.css` link |
| REQ-eliminate-template-drift | Single design language across all routes; no V1/V2 drift | All Phase-6 templates `{% extends "base.html" %}` (the Phase-4 shell); CSS append-only to `zeeker.css` with body-class scoping (`.page-developers`, `.page-status`, …) — no second stylesheet, no `app.css` workarounds |
| REQ-frontend-data-via-http | Frontend reads exclusively via internal HTTP to `http://zeeker-datasette:8001/...json`; no SQLite import | All data fetches go through `datasette_client.py` helpers (`fetch_databases`, `fetch_database`, `fetch_site_metadata`, new: `discover_searchable_tables`, `search_table`, `execute_sql`); zero `import sqlite3` |
| REQ-api-byte-parity | Phase 6 adds NO new datasette routes — gate stays clean; baseline at phase boundary | Phase 6 only adds frontend HTML routes (no `/-/*`, no `.json|.csv|.db`); `verify_api_parity.sh` against `phase-03-pre/` baseline still applies. Plan re-baselines as `phase-06-pre/` per Phase 5 carry-forward |

## Project Constraints (from CLAUDE.md)

The Phase-6 plan must respect these CLAUDE.md directives:

- **No hardcoded database references.** Every aux page that lists databases must iterate `/-/databases.json` (handled). `/sql` landing list is generic; `/sources`, `/developers`, `/llms.txt` already enumerate dynamically.
- **datasette-template-sql** is M1-side (Datasette plugin); frontend does NOT use it. All dynamic content goes through `datasette_client.py` helpers.
- **Self-hosted fonts only** — Inter, JetBrains Mono, Fraunces from `static/fonts/`. Phase 6 adds zero font references; everything reuses `--font-*` tokens already in `:root`.
- **`_zeeker_*` metadata tables are hidden from the UI.** The hidden-table predicate (`t.get("hidden") or t.get("name", "").startswith("_zeeker")`) applies to `/sources`, `/developers`, `/llms.txt`, AND the `/sql` canned-queries listing per D-15.
- **Routes section in CLAUDE.md** already documents the auxiliary route inventory (`/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/-/search`, `/llms.txt`). Phase 6 makes those true at the frontend tier; the plan SHOULD update the `/-/search` reference to `/search` (per D-01) at the same time it lands the route.

## Standard Stack

### Core (already pinned in `packages/zeeker-frontend/pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi[standard]` | 0.136.0 | HTTP framework + form parsing for POST `/sql/{db}` | `[VERIFIED: pyproject.toml]` Already in use Phase 4-5; `Form()` body for textarea is its standard pattern |
| `httpx` | 0.28.1 | Async HTTP client to Datasette | `[VERIFIED: pyproject.toml]` `AsyncClient` + `MockTransport` (used in Phase-5 tests); supports `params` kwarg for safe URL-encoding |
| `jinja2` | 3.1.6 | Templating | `[VERIFIED: pyproject.toml]` Phase 4 wired filters + globals; auto-escape on `.html` files |
| `uvicorn[standard]` | 0.44.0 | ASGI server | `[VERIFIED: pyproject.toml]` |

### Supporting — NEW dependencies Phase 6 introduces

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyyaml` | `>=6.0,<7.0` | Load `data/changelog.yaml` at startup (D-12) | One call: `yaml.safe_load(path.read_text())` in lifespan |
| (optional) `sqlparse` | — | DEFERRED. Plan does NOT add. Plain textarea per PRD Appendix B + D-09 |

`[VERIFIED: live system has pyyaml 6.0.3]` but `[VERIFIED: pyproject.toml]` it is NOT in the frontend's declared deps. **The plan MUST add `pyyaml` to `packages/zeeker-frontend/pyproject.toml`**; otherwise the lifespan boot will `ModuleNotFoundError` inside the Docker container (which uses a clean uv-installed venv per Phase-2 SUMMARY). No alternative needed — YAML is the source format M1 ships and the format ops will edit going forward.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| YAML for changelog | TOML / JSON / Python module | YAML is M1-native (`plugins/strings.yaml`); D-12 explicitly says port the YAML; switching format = unnecessary diff. Stick with YAML. |
| `asyncio.TaskGroup` for fan-out | `asyncio.gather(..., return_exceptions=True)` | TaskGroup cancels siblings on first failure (Python 3.11+ semantics) — DISASTROUS for `/search` where one slow/failing table should not abort the whole search. Use `gather(return_exceptions=True)` — see Pattern 1 below. `[VERIFIED: docs.python.org/3/library/asyncio-task]` |
| `httpx` POST→Datasette for SQL execution | GET with `?sql=…` query | GET is what Datasette accepts and what Caddy's CSV/JSON suffix routing expects (`<a href="/{db}.csv?sql=…">`). POST would require Datasette to accept POST SQL (it does, but with CSRF token); GET is simpler and idempotent. Frontend's POST is just for the form-body shape; the upstream call to Datasette is GET. |
| `cachetools` for FTS-discovery cache | Simple module-level dict | Single key (`app.state.searchable_tables`), no eviction (process-scoped, daily container restart). One dict on `app.state` is sufficient — same reasoning as Phase-4's metadata cache. |
| Native HTML form CSRF | None | Read-only SQL execution; Datasette enforces read-only at engine level. No CSRF token required. `[CITED: docs.datasette.io/en/stable/sql_queries.html#cross-database-queries]` (read-only by default). |

**Installation (additive only):**
```bash
# In packages/zeeker-frontend/
uv add 'pyyaml>=6.0,<7.0'
```

**Version verification (run by plan-author):**
```bash
uv pip view pyyaml      # confirm latest stable
# As of training: pyyaml 6.0.2 is widely deployed; system has 6.0.3.
```
`[ASSUMED]` PyYAML 6.0.x will be the latest stable when Phase 6 lands. If a 7.0 has shipped by then, the plan should pin `>=6.0,<8.0` and the executor verifies via `npm view`-equivalent (`uv pip view`) at install time.

## Architecture Patterns

### System Architecture Diagram

```
                           ┌─────────────────────────────────────────┐
                           │          Browser (data.zeeker.sg)        │
                           └────────────────┬─────────────────────────┘
                                            │ HTTPS
                                            ▼
                           ┌──────────────────────────────────────────┐
                           │           Caddy reverse proxy            │
                           │  @datasette = *.json | *.csv | *.db | /-/*│
                           │  default    = everything else            │
                           └────┬─────────────────────────────┬───────┘
                                │                             │
                            HTML routes                   suffix-matched
                            (incl. /search, /sql)         (.json/.csv/.db, /-/*)
                                │                             │
                                ▼                             ▼
        ┌──────────────────────────────────────┐    ┌──────────────────────────┐
        │     zeeker-frontend  :8000  (FastAPI) │    │   zeeker-datasette :8001 │
        │                                       │    │   (read-only, internal)  │
        │  ┌─ lifespan ──────────────────────┐ │    │                          │
        │  │  app.state.http (AsyncClient)   │ │    │  /-/databases.json       │
        │  │  app.state.searchable_tables    │◄────┼──/{db}.json (fts_table)   │
        │  │  app.state.changelog (YAML)     │ │    │  /{db}/{table}.json      │
        │  └─────────────────────────────────┘ │    │     ?_search=… (FTS)     │
        │                                       │    │  /{db}.json?sql=… (SQL)  │
        │  routes_aux.py        ───────────────┼────┤  /-/metadata.json        │
        │   /developers, /status, /sources,    │    │     databases.{db}.queries│
        │   /about, /how-to-use, /llms.txt     │    │                          │
        │                                       │    │  3s ms_limit             │
        │  routes_search.py     ───────────────┼────┤  1000-row cap            │
        │   /search?q=…  (asyncio.gather       │    │  read-only               │
        │     across searchable_tables)        │    │                          │
        │                                       │    └──────────────────────────┘
        │  routes_sql.py        ───────────────┼─── ↑
        │   /sql       (database list)         │    │
        │   /sql/{db}  GET (textarea + canned) │    │
        │   /sql/{db}  POST (httpx GET to .json)│   │
        │                                       │    │
        │  routes_database.py   (Phase 4)      │    │   Browser fetches CSV/JSON
        │  routes_table.py      (Phase 5)      │    │   downloads DIRECTLY via
        │  routes_row.py        (Phase 5)      │    │   Caddy @datasette matcher
        │  routes_home.py       (Phase 4)      │    │   (does not touch frontend)
        │                                       │    │
        │  StaticFiles mount /static/*          │    │
        │   → robots.txt, fonts, css, js        │    │
        └──────────────────────────────────────┘    │
                                                     │
                            ┌────────────────────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │  Browser CSV / JSON  │
                  │  download link       │
                  │  (suffix-routed)     │
                  └──────────────────────┘

Request flow for GET /search?q=DBS:
  1. Caddy → frontend (default matcher)
  2. routes_search.search(): for each (db, table) in app.state.searchable_tables:
       create asyncio task → app.state.http.get(f"/{db}/{table}.json", params={
         "_search": q, "_size": 10, "_shape": "objects"})
  3. asyncio.gather(*tasks, return_exceptions=True)  # never abort whole search
  4. Group successful results by (db, table); render via search.html template
  5. Cache-Control: public, max-age=60, swr=300

Request flow for POST /sql/{db}:
  1. Caddy → frontend
  2. routes_sql.run(): Form(sql=…, _sql_param_*=…) → httpx.AsyncClient.get(
       f"/{db}.json", params={"sql": sql, **bound_params, "_shape": "objects"})
  3. If response.status_code == 400: parse body, render with error block
  4. If response.status_code == 200: render results table + truncation banner if needed
  5. Render export anchors as plain hrefs to /{db}.csv?sql=… (Caddy routes direct)
  6. Cache-Control: no-store
```

### Recommended Project Structure

```
packages/zeeker-frontend/src/zeeker_frontend/
├── main.py                  # +3 router includes; +lifespan extension
├── datasette_client.py      # +discover_searchable_tables, +search_table, +execute_sql
├── routes_aux.py            # NEW: /developers /status /sources /about /how-to-use /llms.txt /robots.txt
├── routes_search.py         # NEW: /search
├── routes_sql.py            # NEW: /sql /sql/{db} (GET + POST)
├── changelog.py             # NEW: thin module that loads data/changelog.yaml at boot
├── data/
│   └── changelog.yaml       # NEW: ported from plugins/strings.yaml recent_updates list
├── templates/
│   ├── base.html            # 1-line edit: nav Search href /-/search → /search
│   ├── pages/               # NEW directory for aux templates
│   │   ├── developers.html
│   │   ├── status.html
│   │   ├── sources.html
│   │   ├── about.html
│   │   ├── how-to-use.html
│   │   ├── search.html      # State A + State B in one template (q present/absent)
│   │   ├── sql_index.html   # /sql landing
│   │   └── sql_db.html      # /sql/{db} editor + results
│   ├── _partials/
│   │   ├── api_table.html   # NEW: 2-col API parameter table partial (used twice on /developers)
│   │   ├── method_card.html # NEW: numbered method-card partial (about + how-to-use)
│   │   ├── example_box.html # NEW: copy-button + <pre><code> partial
│   │   ├── search_result.html  # NEW: one .search-result item
│   │   └── timeline_item.html  # NEW: status update row
│   └── llms.txt             # NEW: Jinja text/plain template (no extends)
└── static/
    ├── robots.txt           # NEW: verbatim from M1 templates/pages/robots.txt
    ├── css/zeeker.css       # APPEND ONLY: Phase-6 section before FOOTER LINK OVERRIDE block
    └── js/aux.js            # NEW (optional): copy-btn + canned-query prefill (~15 lines, no deps)
```

### Pattern 1: `/search` Fan-out with Partial-Failure Tolerance

```python
# routes_search.py — handler (excerpt)
import asyncio
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


async def _safe_search_one(client, db, table, q, size):
    """One per-table FTS call; raises NEVER — all errors converted to None."""
    try:
        r = await client.get(
            f"/{db}/{table}.json",
            params={"_search": q, "_size": size, "_shape": "objects"},
            timeout=httpx.Timeout(3.0, connect=1.0),
        )
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError):
        return None  # caller treats None as "table errored, drop the group"


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", _retry: int = 0):
    client = request.app.state.http
    searchable: dict[str, list[str]] = request.app.state.searchable_tables

    if not q.strip():
        # State A — render hero search + tips (no fan-out)
        response = request.app.state.templates.TemplateResponse(
            request=request,
            name="pages/search.html",
            context={"q": "", "groups": [], "page_class": "page-search",
                     "breadcrumbs": [{"label": "Search"}]},
        )
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        return response

    # State B — fan out
    pairs = [(db, t) for db, ts in searchable.items() for t in ts]
    tasks = [_safe_search_one(client, db, t, q, 10) for db, t in pairs]
    # asyncio.gather + return_exceptions: NEVER abort siblings on one failure.
    # `_safe_search_one` already converts errors to None, so return_exceptions is belt-and-suspenders.
    results = await asyncio.gather(*tasks, return_exceptions=True)

    groups, failures = [], 0
    for (db, t), r in zip(pairs, results):
        if r is None or isinstance(r, BaseException):
            failures += 1
            continue
        rows = r.get("rows") or []
        if not rows:
            continue   # skip 0-result groups per UI-SPEC
        groups.append({
            "db": db, "table": t,
            "count": r.get("filtered_table_rows_count") or len(rows),
            "rows": rows[:10],
            "primary_keys": r.get("primary_keys") or [],
        })
    groups.sort(key=lambda g: (g["db"], g["table"]))

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/search.html",
        context={
            "q": q,
            "groups": groups,
            "failures": failures,
            "total_count": sum(g["count"] for g in groups),
            "n_databases": len({g["db"] for g in groups}),
            "page_class": "page-search",
            "breadcrumbs": [{"label": "Search"}],
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

**Why `gather(return_exceptions=True)` not `TaskGroup`:** `asyncio.TaskGroup` (Python 3.11+) cancels all sibling tasks on first failure. For `/search` that means one timeout would abort every other table's results. `[CITED: docs.python.org/3/library/asyncio-task.html#task-groups]` `[CITED: docs.python.org/3/library/asyncio-task.html#asyncio.gather]` (return_exceptions defers errors as values).

### Pattern 2: FTS-Discovery Probe (Lifespan Extension)

```python
# datasette_client.py — new helper
async def discover_searchable_tables(client: httpx.AsyncClient) -> dict[str, list[str]]:
    """Return {db_name: [table_names_with_fts]}. Called once at lifespan boot.

    Live-verified shape: each /{db}.json table dict has an `fts_table` field
    that is a string (FTS counterpart name) when the table has FTS, or null/None
    when it doesn't. Hidden tables (the FTS internals themselves: *_fts, *_fts_data)
    have hidden=True AND should be filtered out of search targets.
    """
    out: dict[str, list[str]] = {}
    try:
        dbs = await fetch_databases(client)  # already exists; returns list[{name, ...}]
    except httpx.HTTPError:
        return out  # boot continues with empty cache; /search renders 503 friendly
    for entry in dbs:
        db = entry["name"]
        try:
            payload = await fetch_database(client, db)  # already exists
        except httpx.HTTPError:
            continue
        if payload is None:
            continue
        names = []
        for t in payload.get("tables") or []:
            if t.get("hidden"):
                continue
            if t.get("name", "").startswith("_zeeker"):
                continue
            if t.get("fts_table"):       # ← the canonical signal (live-verified)
                names.append(t["name"])
        if names:
            out[db] = names
    return out

# main.py — lifespan extension
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(...)  # existing
    app.state.searchable_tables = await discover_searchable_tables(app.state.http)
    app.state.changelog = _load_changelog()  # see Pattern 3
    try:
        yield
    finally:
        await app.state.http.aclose()
```

`[VERIFIED: live datasette /sglawwatch.json fields]` — each table object includes `fts_table: <name> | null`. This is THE signal; do not infer from sibling `_fts` virtual tables. The plan should call out this verified field name in the docstring so the executor doesn't second-guess and try to grep `db.execute("PRAGMA table_list")` (which would re-introduce SQLite-side dependencies and break REQ-frontend-data-via-http).

### Pattern 3: Changelog Loader (One-Shot at Boot)

```python
# changelog.py
from __future__ import annotations
from pathlib import Path
import yaml

_DATA_DIR = Path(__file__).parent / "data"


def load_changelog() -> list[dict]:
    """Return list of {date, type, title, description} dicts.

    Empty list on any failure — the page degrades to "No updates yet".
    """
    p = _DATA_DIR / "changelog.yaml"
    if not p.exists():
        return []
    try:
        doc = yaml.safe_load(p.read_text()) or {}
        items = doc.get("recent_updates") or []
        return [i for i in items if isinstance(i, dict) and "date" in i]
    except Exception:
        return []
```

Source format (port from `plugins/strings.yaml`):
```yaml
# packages/zeeker-frontend/src/zeeker_frontend/data/changelog.yaml
recent_updates:
  - date: "2025-06-09"
    type: "feature"
    title: "data.zeeker.sg launches!"
    description: "Everything is new and shiny here!"
  - date: "2025-05-16"
    type: "data"
    title: "Sglawwatch -- headlines starts"
    description: "Legal News in Singapore selected by Editors starts compiling and automatic updates"
```

### Pattern 4: SQL Execution with Friendly Error Handling

```python
# routes_sql.py (excerpt)
import re
import httpx
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


def _detect_params(sql: str) -> list[str]:
    """Return param names in :param order, deduped while preserving order."""
    seen, out = set(), []
    for m in _PARAM_RE.finditer(sql):
        n = m.group(1)
        if n not in seen:
            seen.add(n); out.append(n)
    return out


@router.post("/sql/{db}", response_class=HTMLResponse)
async def run_sql(request: Request, db: str, sql: str = Form(...)):
    client: httpx.AsyncClient = request.app.state.http
    form = await request.form()
    param_values = {
        k.removeprefix("_sql_param_"): v
        for k, v in form.items()
        if k.startswith("_sql_param_")
    }

    # Build datasette params: {sql, _shape, _param_name → value, ...}
    ds_params = {"sql": sql, "_shape": "objects"}
    for name in _detect_params(sql):
        if name in param_values:
            ds_params[f"_param_{name}"] = param_values[name]
    # Fall through: if a :param wasn't filled, datasette returns its own
    # "Missing argument" error — render it the same way as any SQL error.

    error, results = None, None
    try:
        r = await client.get(f"/{db}.json", params=ds_params)
        body = r.json()
        if r.status_code == 400:
            # Verified live: 400 returns full JSON with `error` populated.
            error = body.get("error") or "Query failed"
        elif r.status_code == 404:
            raise HTTPException(404, "Database not found")
        else:
            r.raise_for_status()
            error = body.get("error")
            if not error:
                results = body
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/sql_db.html",
        context={
            "database": db,
            "sql": sql,
            "results": results,         # {rows, columns, truncated, query_ms} or None
            "error": error,             # str or None
            "page_class": "page-sql-db",
            # canned-queries + breadcrumbs computed elsewhere
        },
    )
    response.headers["Cache-Control"] = "no-store"   # D-14
    return response
```

`[VERIFIED: live curl]` — `GET /sglawwatch.json?sql=SELECT+*+FROM+nonexistent_table` returns HTTP **400** with body `{"ok": false, "error": "no such table: nonexistent_table", "rows": [], "columns": [], "truncated": false, "query_ms": 0.67, …}`. Naive `r.raise_for_status()` would crash before we read the friendly error — handler MUST inspect the body on 400 (and only on 400). Successful queries return HTTP 200 with `error: null`.

### Pattern 5: `/llms.txt` Plain-Text Renderer

```python
# routes_aux.py (excerpt)
from fastapi.responses import PlainTextResponse

@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt(request: Request):
    client = request.app.state.http
    try:
        dbs = await fetch_databases(client)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")

    db_blocks = []
    for entry in dbs:
        db = entry["name"]
        try:
            payload = await fetch_database(client, db)
        except httpx.HTTPError:
            continue
        if payload is None:
            continue
        tables = [
            t for t in (payload.get("tables") or [])
            if not t.get("hidden") and not t.get("name", "").startswith("_zeeker")
        ]
        db_blocks.append({
            "name": db,
            "description": payload.get("description") or "",
            "tables": tables,
        })

    body = request.app.state.templates.get_template("llms.txt").render(
        databases=db_blocks,
    )
    response = PlainTextResponse(content=body, media_type="text/plain; charset=utf-8")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

The `llms.txt` Jinja template is a plain-text Jinja file (Jinja2's `Environment` does NOT autoescape `.txt` extensions — exactly what we want for plain-text body). Body shape MUST match `plugins/developers_page.py:81-121` so existing LLM consumers can ingest it.

### Anti-Patterns to Avoid

- **`asyncio.TaskGroup` for `/search` fan-out.** Cancels siblings on first failure — exact opposite of what we want. Use `gather(return_exceptions=True)`.
- **`r.raise_for_status()` before checking SQL response body.** Datasette returns 400 for SQL errors with a populated `error` field; raising early loses the friendly message.
- **Inferring FTS counterparts by string-matching `_fts` suffix tables.** Datasette already reports `fts_table` per row — use the field. Inference would break for non-standard FTS naming and double-count (FTS internal tables themselves carry `fts_table` to point to themselves).
- **Re-deriving sketch-findings tokens.** Aux CSS is APPEND-ONLY. No `:root` edits. No new tokens. Body-class scoping (`.page-developers .api-table`, etc.) keeps Phase-6 selectors from leaking into Phase 4-5.
- **Modifying the Caddyfile.** D-01/D-02 lock `/-/*`. Frontend NEVER registers under `/-/`.
- **Re-baselining mid-phase or skipping the parity check.** REQ-api-byte-parity gate stays clean precisely because Phase 6 adds no `.json|.csv|.db|/-/` routes.
- **Forwarding raw form data to Datasette without an allowlist.** Phase 5's `_TABLE_ALLOWED_PARAMS` pattern applies: build a fresh `ds_params` dict explicitly, never `params=request.query_params`.
- **Registering routers AFTER `database_router` / `routes_table_router`.** FastAPI matches first registered; the catch-all `/{db}` will eat `/search`, `/sql`, `/sources`, etc. if they register later.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FTS execution | A custom SQLite reader | Datasette's `_search` query param | Datasette already exposes BM25/rank() via `/{db}/{table}.json?_search=…&_size=N`; D-03 |
| SQL execution + safety | A query parser/sandbox | Datasette's read-only mode + `ms_limit=3000` + 1000-row cap | D-08 trusts these; PRD §10 reaffirms |
| YAML loading | A custom front-matter parser | `yaml.safe_load` | Single function call for D-12 |
| Param substitution | Manual `:name` regex replacement IN the SQL string | Datasette's `_param_<name>` URL params | Datasette binds via prepared-statement-style placeholders; passing param strings via `_param_x=…` is safer than client-side substitution which would re-introduce injection risk |
| Cross-database FTS ranking | Cross-engine BM25 normalization | Group-by-table presentation (D-05) | FTS5 ranks are not comparable across indexes; D-05 explicitly accepts within-group ranking only |
| Concurrent HTTP fan-out | A custom `httpx` thread pool | `asyncio.gather(return_exceptions=True)` | Stdlib; 1 line; idiomatic for single-event-loop FastAPI |
| Copy-to-clipboard | Importing clipboard.js | `navigator.clipboard.writeText(...)` | 5 lines vanilla JS; no dependency; well-supported in 2026 browsers |
| SQL syntax highlighting | Prism / CodeMirror | Plain `<textarea>` | PRD Appendix B explicitly defers; D-09 keeps deferred. Plain textarea ships in v1. |
| `<details>` accordion for canned queries | Custom JS show/hide | Native `<details><summary>` | Zero JS; full keyboard accessibility built-in |
| Static file serving (`robots.txt`) | A FastAPI handler | Existing `StaticFiles` mount at `/static/*` + a route alias | Caddy's default matcher passes `/robots.txt` (no suffix `.json|.csv|.db`, not `/-/*`) to frontend. EITHER (a) a 1-line `@router.get("/robots.txt", response_class=FileResponse)` returning `static/robots.txt`, OR (b) drop into `static/` and a route alias `/robots.txt → /static/robots.txt`. (a) is simpler — see Recommendation in §Specifics. |

**Key insight:** Phase 6 is mostly a port. The temptation is to "improve" things — add caching layers, custom SQL parsing, fuzzy search ranking, syntax highlighting. RESIST. The locked decisions (D-08 trust Datasette safeguards, D-09 v1 param binding, no syntax highlighting) reflect real PRD scope. Stay inside that envelope; defer everything else to Phase 8.

## Common Pitfalls

### Pitfall 1: SQL errors are HTTP 400, not HTTP 200

**What goes wrong:** Naive handler does `r = await client.get(...); r.raise_for_status(); body = r.json()`. On any SQL error (typo, missing table, ms_limit hit), Datasette returns HTTP 400 — `raise_for_status()` raises `httpx.HTTPStatusError`, the handler catches it as "upstream failure" and returns 503 — user sees "Data API unavailable" instead of the friendly error message Datasette already prepared.

**Why it happens:** REST conventions usually pair 4xx with terminal failure. Datasette's SQL endpoint, however, returns 400 + a fully-populated `error` field for client-error SQL — the body is the message you want to display.

**How to avoid:** Inspect the body on 400 before raising. See Pattern 4. Specifically: if `r.status_code == 400 and "error" in r.json()`, treat it as a **rendered error response**, not a transport failure.

**Warning signs:** `/sql/{db}` test cases for malformed SQL produce 503 instead of an inline error block.

### Pitfall 2: `asyncio.TaskGroup` aborts the search on first failure

**What goes wrong:** With `TaskGroup`, one slow table (timeout) or 5xx aborts every other table's request — user sees an empty `/search` page even though 9 of 10 tables succeeded.

**Why it happens:** `TaskGroup` semantics (Python 3.11+) are designed for "all or nothing" group operations: any task raising cancels its siblings.

**How to avoid:** Use `asyncio.gather(*coros, return_exceptions=True)`. Wrap the per-table coro to convert exceptions to a sentinel value (`None`) so the result iteration is uniform. See Pattern 1. `[CITED: docs.python.org/3/library/asyncio-task.html#asyncio.gather]`

**Warning signs:** `/search?q=x` with one deliberately-failing table returns 0 groups.

### Pitfall 3: Routing registration order eats new routes

**What goes wrong:** `@app.get("/search")` registered AFTER `app.include_router(database_router)` (which has `/{db}`) — FastAPI's path matcher tries `/{db}` first and matches with `db="search"`, frontend tries to fetch `/search.json` from Datasette, gets 404, returns "Database not found" 404. The new `/search` route never runs.

**Why it happens:** FastAPI matches routes in registration order; `/{db}` is a catch-all for any single-segment path.

**How to avoid:** Register Phase-6 routers BEFORE `database_router` and `routes_table_router`:
```python
# main.py
app.include_router(home_router)              # /
app.include_router(aux_router)               # /developers, /status, /sources, /about, /how-to-use, /llms.txt, /robots.txt
app.include_router(search_router)            # /search
app.include_router(sql_router)               # /sql, /sql/{db}
app.include_router(database_router)          # /{db}    ← CATCH-ALL
app.include_router(table_router)             # /{db}/{table}
app.include_router(row_router)               # /{db}/{table}/{pk}
```

**Warning signs:** Curling `/search` returns 404 with `{"detail": "Database not found"}` instead of HTML.

### Pitfall 4: Hidden filter must run on TWO predicates

**What goes wrong:** A page lists `_zeeker_schemas`/`_zeeker_updates` (which have `hidden: false` in `/{db}.json` because per-database overlay metadata didn't carve them out). Or it lists `headlines_fts` (which has `hidden: true` and `name: "headlines_fts"` — fine, single predicate would also catch it).

**Why it happens:** Datasette's `hidden` flag is set by per-database `metadata.json` opt-in. Not every overlay sets it. The `_zeeker_*` prefix is the platform convention; `hidden` is the FTS-internals convention. Both must be checked.

**How to avoid:** `t.get("hidden") or t.get("name", "").startswith("_zeeker")` — the predicate Phase 4 + 5 already use. Apply on `/sources`, `/developers`, `/llms.txt`, AND on `/sql/{db}` canned-queries listing per D-15.

`[VERIFIED: live /sglawwatch.json]` confirms `_zeeker_schemas` and `_zeeker_updates` have `hidden: false` and would leak without the prefix predicate.

**Warning signs:** `/sources` lists `_zeeker_schemas` as a "table" in any database.

### Pitfall 5: `/{db}.json?sql=…` body shape changes with `_shape`

**What goes wrong:** Without `_shape=objects`, `rows` is a positional list (`[[1, "hi"], [2, "world"]]`) — Jinja's `{{ row.title }}` returns nothing. With `_shape=objects`, `rows` is `[{"id": 1, "name": "hi"}, ...]`. Same endpoint, two return shapes.

**Why it happens:** Datasette's default shape is `arrays`; the `_shape` parameter controls dict-vs-list-of-list.

**How to avoid:** ALWAYS pass `_shape=objects` (existing `fetch_table` already does this; replicate in `execute_sql` and `search_table`). Templates can then rely on `{{ row[col] }}` or `{{ row.col_name }}`.

**Warning signs:** `/sql/{db}` results table renders empty cells; `/search` excerpts are blank.

### Pitfall 6: Datasette `next_url` is fully-qualified to internal hostname

**Carry-forward from Phase 5 Pitfall 2.** Doesn't apply to `/search` (no pagination — top-10-per-table only) or `/sql/{db}` (no pagination, just the 1000-row cap). Mentioned for completeness so the executor doesn't reach for `next_url` patterns and accidentally leak `zeeker-datasette:8001` into HTML.

### Pitfall 7: SQL param-binding via URL query smuggling

**What goes wrong:** Form contains `_sql_param_id=42&_sql_param_name=foo&extra=evil` and the handler does `httpx.get(f"/{db}.json", params=request.form())`. Now `extra=evil` is forwarded to Datasette — and any future Datasette feature that uses `extra` becomes attacker-controlled.

**Why it happens:** Same SSRF-ish surface as Phase 5 Pitfall 7 (querystring smuggling). Datasette accepts unknown params silently.

**How to avoid:** Allowlist. Build `ds_params` explicitly:
```python
ds_params = {"sql": sql, "_shape": "objects"}
for name in _detect_params(sql):              # only :params present in the SQL
    if name in param_values:                   # only values the user actually submitted
        ds_params[f"_param_{name}"] = param_values[name]
```
Drop everything else.

**Warning signs:** Anything in `request.form()` keys other than `sql` and `_sql_param_*`.

### Pitfall 8: `Jinja2Templates` autoescape doesn't apply to `.txt`

**What goes wrong:** Rendering `llms.txt` with `<` or `&` in a database description leaks them as `&lt;` / `&amp;` — but the response is `text/plain`, so users see literal HTML entities in their LLM ingest pipeline.

**Why it happens:** Starlette's `Jinja2Templates` uses Jinja's `select_autoescape(['html', 'htm', 'xml'])` — `.txt` is OFF, which is what we want. But ANY filter chain that does `{{ x|e }}` re-introduces escaping.

**How to avoid:** In `llms.txt` Jinja template, do NOT use `|e` or `{% autoescape on %}`. Use `{{ value }}` plain. If a value might genuinely break the format (newlines in description), strip/replace at handler level.

**Warning signs:** `curl /llms.txt | grep '&amp;'` returns hits.

### Pitfall 9: `/-/search` and `/-/sql` carve-out is fragile

**What goes wrong:** Phase 5 verifier check #M asserts `/-/search` reaches Datasette via Caddy. If a future Phase-6 router accidentally registers `@app.get("/-/search")`, FastAPI accepts it but Caddy still routes `/-/*` to Datasette — so the handler is dead code. Worse: if a planner forgets D-01 and tries to redirect `/-/search → /search` from the frontend, the redirect handler is invisible to users (Caddy diverted before reaching frontend).

**Why it happens:** D-01/D-02 lock `/-/*` to Caddy → Datasette. Anything frontend mounts under `/-/` is functionally invisible.

**How to avoid:** No frontend route registers under `/-/`. Code review check. If a redirect from `/-/search` to `/search` is desired later, it requires a Caddyfile carve-out — explicitly out of Phase 6 scope (Deferred Idea in CONTEXT.md).

**Warning signs:** Any `@router.get("/-/...")` in `routes_*.py`.

### Pitfall 10: Empty `searchable_tables` cache after boot failure

**What goes wrong:** Datasette is slow to start; lifespan probe fires while Datasette returns 503 on `/-/databases.json`. `discover_searchable_tables` swallows the error and returns `{}`. `/search?q=x` then fans out across zero tables — renders an empty results page despite tables existing.

**Why it happens:** D-04 explicitly accepts process-lifetime caching with no TTL. A boot-time blip never recovers until the next container restart (which is daily, but still).

**How to avoid:** TWO mitigations:
1. **Boot ordering** — `docker-compose.yml` already sets `depends_on: zeeker-datasette` with a healthcheck (Phase 2). Verify the frontend lifespan won't run until `/-/databases.json` is reachable. If Datasette is 503 for 30s+, accept the empty cache (rare in practice).
2. **Friendly 503** — when `app.state.searchable_tables == {}` AND `q` is non-empty, render a 503 with the copy from UI-SPEC: "Search temporarily unavailable. Try again in a minute." Better UX than a misleading 0-results page.

**Warning signs:** `/search?q=x` returns 200 with 0 groups when known FTS tables exist.

## Runtime State Inventory

> Phase 6 is greenfield code addition + an in-place CSS append. No rename, no refactor of stored data. This section is included for completeness; nothing in any category requires migration tasks.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified by reading `plugins/strings.yaml` (port from YAML to YAML, same schema) and inspecting Datasette tables (no DB-schema changes). | None |
| Live service config | None — Caddyfile NOT modified (D-01/D-02). Docker Compose NOT modified beyond what's already there (frontend image rebuild only). | None |
| OS-registered state | None — no cron, no launchd, no Task Scheduler tasks reference Phase-6 code paths. | None |
| Secrets/env vars | None — no new env vars. `ZEEKER_DATASETTE_URL` (Phase 4) reused. | None |
| Build artifacts | Frontend image must be rebuilt (`docker compose build frontend`) so the appended `zeeker.css`, new templates, new `data/changelog.yaml`, and new pyproject `pyyaml` dep are baked in. M1 `packages/zeeker-datasette/` plugins remain in place; Phase 7 deletes them. | Container rebuild (already part of every deploy). |

## Common Pitfalls (continued — Verifier-Only Edge Cases)

### Pitfall 11: Phase 5 verifier still asserts "Phase-6 routes 404"

**What goes wrong:** Phase-6 lands `/developers` etc. that return 200, but the existing `verify_phase_05.sh` section M still asserts they 404 — `bash scripts/verify_phase_05.sh` now fails on the live system even though everything is correct.

**Why it happens:** Phase 5's verifier preserves the boundary contract; flipping the assertion requires editing it.

**How to avoid:** Phase 6 verifier strategy: AUTHOR a NEW `verify_phase_06.sh` (don't edit `verify_phase_05.sh`) that:
1. Delegates to Phase-4 invariants (`bash scripts/verify_phase_04.sh`) — keeps Caddy + topology + home/database checks.
2. Re-runs the Phase-5 table/row checks INLINE (the parts that don't include the Phase-6 boundary) — copy section B-L.
3. Adds Phase-6 positive asserts: every aux route 200 + italic-accent H1 + frontend CSS link.
4. Re-runs API parity vs `phase-03-pre/` baseline.

This matches the Phase-5 model (extend Phase-4) without a destructive `verify_phase_05.sh` edit. Keep `verify_phase_05.sh` intact for historical regression replay.

Alternative simpler strategy: parametrize Phase-5's section M with an env var (`PHASE_6_LIVE=1`) that flips the assertion polarity. The plan author picks; both are acceptable.

### Pitfall 12: `pyyaml` import error inside Docker container

**What goes wrong:** `data/changelog.yaml` loads at lifespan boot, but `import yaml` inside the container raises `ModuleNotFoundError` because the dep wasn't added to `pyproject.toml`. Container fails health check; Caddy 502s.

**Why it happens:** PyYAML is on the dev machine system Python (`6.0.3`) but NOT in `packages/zeeker-frontend/pyproject.toml`'s `[project] dependencies`. Docker build uses a clean uv-installed venv.

**How to avoid:** Plan task explicitly adds `pyyaml>=6.0,<7.0` to `pyproject.toml`. Container build (`docker compose build frontend`) installs it. Ship-checkpoint runs `python -c "import yaml; print(yaml.__version__)"` inside the container as a smoke check.

### Pitfall 13: `/robots.txt` served from frontend or static — pick ONE

**What goes wrong:** Two implementations co-exist (StaticFiles serves `/static/robots.txt`, plus a redundant `@router.get("/robots.txt")`). Caddy routes `/robots.txt` to frontend (no suffix match), frontend's main router resolves to one or the other depending on registration order, and the OTHER becomes dead code that tests exercise.

**How to avoid:** Pick the cleaner option:

- **Recommended:** Single `FileResponse` handler in `routes_aux.py`:
  ```python
  @router.get("/robots.txt", response_class=PlainTextResponse)
  async def robots_txt():
      return PlainTextResponse(
          (Path(__file__).parent / "static" / "robots.txt").read_text(),
          media_type="text/plain; charset=utf-8",
      )
  ```
  Reason: keeps the file under `static/` (so `docker cp` copies it to the image), but the URL `/robots.txt` is server-rendered with explicit content-type. Avoids the `/static/robots.txt` URL leak in HTML (Web crawlers expect the file at the URL root, not under `/static/`).

- **Alternative:** Drop `robots.txt` into `static/` and rely on `app.mount("/static", ...)`. URL becomes `/static/robots.txt`, NOT `/robots.txt` — search engines miss it.

Plan locks on the first option. Verifier asserts `curl -fsS http://localhost/robots.txt` returns 200 + `Content-Type: text/plain`.

## Code Examples

Verified patterns from official sources and live system probes:

### FTS table fan-out (`/search`)

```python
# Verified live: /sglawwatch.json table dicts include "fts_table" string-or-null.
# Discovery walks every database once at boot, then /search just iterates the cache.
async def search_table(client, db, table, q, size):
    r = await client.get(
        f"/{db}/{table}.json",
        params={"_search": q, "_size": size, "_shape": "objects"},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()  # {rows, columns, primary_keys, filtered_table_rows_count, query_ms, ...}
```

### Canned-query metadata access

```python
# Verified live: /-/metadata.json structure:
#   {"databases": {"<db>": {"queries": {"<name>": {"sql": "...", "title": "...", "params": [...]}}}}}
# Currently NO databases on production define queries; the path must be defensive.
def get_canned_queries(site_metadata: dict, db: str) -> dict[str, dict]:
    return ((site_metadata.get("databases") or {}).get(db) or {}).get("queries") or {}
```

### SQL execution with bound params

```python
# Verified live: /sglawwatch.json?sql=SELECT+1+as+a,+'hi'+as+b returns 200 with:
#   {"ok": true, "rows": [[1, "hi"]],  // (positional without _shape)
#    "rows": [{"a": 1, "b": "hi"}],     // (with _shape=objects)
#    "columns": ["a", "b"], "truncated": false, "query_ms": 1.0, "error": null, ...}
async def execute_sql(client, db, sql, params=None):
    ds_params = {"sql": sql, "_shape": "objects"}
    for name, value in (params or {}).items():
        ds_params[f"_param_{name}"] = value
    r = await client.get(f"/{db}.json", params=ds_params)
    if r.status_code == 404:
        return None, "Database not found"
    body = r.json()
    if r.status_code == 400:
        return None, body.get("error") or "Query failed"
    r.raise_for_status()
    return body, body.get("error")  # body.error may be None on success
```

### `<details>`-based canned queries (no JS dependency)

```html
<!-- pages/sql_db.html (excerpt) — works keyboard-only without JS. JS adds prefill behavior. -->
{% if canned %}
<details class="canned-queries">
  <summary>Saved queries ({{ canned|length }})</summary>
  <ul>
    {% for name, q in canned.items() %}
    <li>
      <button type="button"
              class="canned-query"
              data-sql="{{ q.sql|e }}"
              data-params='{{ (q.params or [])|tojson|e }}'>
        {{ q.title or name }}
      </button>
    </li>
    {% endfor %}
  </ul>
</details>
{% endif %}
```

```js
// static/js/aux.js — 8 lines, no dependencies
document.querySelectorAll(".canned-query").forEach(btn => {
  btn.addEventListener("click", () => {
    const ta = document.querySelector("textarea[name=sql]");
    if (ta) { ta.value = btn.dataset.sql; ta.focus(); }
    // Optional: reveal .sql-param-row when btn.dataset.params has items.
  });
});
```

### `/llms.txt` Jinja template (text/plain)

```jinja
# data.zeeker.sg
> Open legal data platform providing structured access to Singapore legal datasets

## API
Base URL: https://data.zeeker.sg

## Endpoints
- GET /{database}/{table}.json - Table data as JSON
- GET /{database}/{table}.csv - Table data as CSV
- GET /{database}.json?sql={query} - Execute SQL query
- GET /-/search.json?q={query} - Full-text search

## Databases
{% for db in databases %}
### {{ db.name }}
{%- if db.description %}
{{ db.description }}
{%- endif %}
Tables:
{%- for t in db.tables %}
- {{ t.name }}{% if t.count %} ({{ t.count }} rows){% endif %}: {{ t.columns|join(", ") }}
{%- endfor %}

{% endfor %}
## Parameters
- _size: Number of rows (default 100, max 1000)
- _next: Pagination token
- _shape: Response shape (objects, arrays, array, object)
- _sort: Sort by column
- _sort_desc: Sort descending by column
```

Note: `/llms.txt` deliberately keeps the legacy `/-/search.json?q=…` reference (per UI-SPEC: `/llms.txt` body shape matches M1 `developers_page.llms_txt` 1:1). The user-facing `/search` UI replaces `/-/search` for humans; the API entry remains documented as `/-/search.json` (still served by Datasette via Caddy).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datasette-search-all` plugin for cross-DB search | Frontend fan-out across `app.state.searchable_tables` | This phase (D-03) | Eliminates HTML-only plugin; frontend owns the search UX |
| `plugins/strings.yaml recent_updates` loaded by `string_manager.py` | `data/changelog.yaml` loaded at frontend lifespan | This phase (D-12) | Frontend-owned; Phase 7 can delete `string_manager.py` cleanly |
| `developers_page.py` / `status_page.py` / `sources_page.py` Datasette plugins | FastAPI handlers in `routes_aux.py` | This phase (D-11) | Single template family in `packages/zeeker-frontend/templates/`; M1 templates removed in Phase 7 |
| M1 `templates/pages/*.html` `{% extends "default:base.html" %}` | Frontend `{% extends "base.html" %}` | This phase (D-11 implicit) | No `default:` namespace prefix; no Datasette-template tilde escaping; no `_header.html` / `_footer.html` includes |
| `<a href="/-/search?q=…">` in M1 `how-to-use.html` | `<a href="/search?q=…">` in ported template | This phase (D-01 + UI-SPEC §Footer Link Carry-Forward) | Two URL conventions co-exist (Datasette `/-/search` for devs; frontend `/search` for users); user-visible nav points at the new path |

**Deprecated/outdated for Phase 6:**
- `plugins/template_filters.py` `pluralize` / `safe_format` / `filesizeformat` — already ported by Phase 4 to `filters.py`. Reuse directly, no edits.
- `static/css/zeeker-base.css` — reference material for harvest only. Phase 7 deletes it from `packages/zeeker-datasette/`.
- M1 `templates/pages/about.html` `<a href="/-/metadata">API Documentation</a>` — re-point to `/developers` per UI-SPEC copywriting contract. (M1 had this wrong; Phase 6 fixes it during the port.)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PyYAML 6.0.x is the latest stable when Phase 6 ships (vs. a 7.0 release between now and merge). | Standard Stack | Low. If 7.0 ships and breaks API, plan widens pin or pins to 6.x explicitly. Verified at install time by executor. |
| A2 | Frontend Docker build uses a clean uv venv (per Phase 2 SUMMARY) — i.e., `pyyaml` MUST be in `pyproject.toml` to reach the container. | Pitfall 12 | Medium-low. Plan adds the dep as a discrete task; verifier smoke-runs `import yaml` inside the running container. |
| A3 | Datasette's `_param_<name>` URL convention binds positional args to `:name` placeholders without further escaping. | Pattern 4 | Low. `[CITED: docs.datasette.io/en/stable/sql_queries.html#named-parameters]` confirms `_<name>=value` binding. |
| A4 | Caddy's default matcher routes `/robots.txt` to frontend (i.e., `.txt` is not in the `@datasette` suffix list). | Pitfall 13 | Low — confirmed by reading the Caddyfile in Phase 3; only `*.json|*.csv|*.db|/-/*` divert. `.txt` falls through to default. Verifier explicitly checks `curl /robots.txt` returns 200 from frontend. |
| A5 | Daily container restart is sufficient cache invalidation for `app.state.searchable_tables` (no in-day FTS topology changes). | D-04 (locked in CONTEXT.md) | Risk owned by user via D-04. If a new FTS table is added mid-day, search misses it until the next deploy. Acceptable per CONTEXT.md. |
| A6 | The Phase-6 verifier should AUTHOR a new `verify_phase_06.sh` and not destructively edit `verify_phase_05.sh`. | Pitfall 11 | Low. Mirrors the Phase-5 model that delegated to Phase-4. Plan locks this; alternate (env-var polarity flip) called out. |

## Open Questions (RESOLVED)

1. **Should `/sql/{db}` GET render an empty editor (no `sql` param), and does `Reset` link rely on this?**
   - What we know: UI-SPEC §Interaction Contracts explicitly says "Reset link: GET to `/sql/{db}` with no query — clears the textarea (handler-side: the template renders empty textarea when `sql is None`)." So GET handler MUST exist and render an empty form.
   - What's unclear: should GET also accept `?sql=…` and pre-populate (for shareable URLs)? CONTEXT.md is silent.
   - **RESOLVED:** yes. Implement `GET /sql/{db}` as render-only (no execution; just template with `sql=request.query_params.get("sql")`) so URLs like `/sql/sglawwatch?sql=SELECT…` render the textarea pre-filled but do NOT auto-run. Auto-run only on POST. This matches Datasette's `/-/sql?sql=…` UX convention. Implemented by Plan 06-05 task `sql_db_get`.

2. **Empty FTS-discovery cache on boot — render `/search` how?**
   - What we know: UI-SPEC §Error states says 503 with friendly copy when discovery fails AND `q` is non-empty.
   - What's unclear: `q` empty (State A) — should it still render with the hero + tips even when discovery is empty? Yes. State A is informational; no fan-out happens.
   - **RESOLVED:** 503 only on State B with empty cache. State A always renders. Plan-author confirms. Implemented by Plan 06-04 `routes_search.py` empty-cache branch.

3. **Does `/about` still link to `/-/metadata`?**
   - What we know: M1 `about.html` line 102: `<a href="/-/metadata">API Documentation</a>`. UI-SPEC §Copywriting says button should be "API Documentation" → `/developers`.
   - What's unclear: is the M1 link a bug worth fixing during the port (yes per UI-SPEC), or a separate concern?
   - **RESOLVED:** fix during the port. This is exactly the kind of "stale reference" CONTEXT.md §Discretion authorizes deviation for. New target: `/developers`. Implemented by Plan 06-03 `about.html` template port.

4. **Should canned-query params be exposed as `<input type=text>` for all types, or typed (number, date)?**
   - What we know: D-09 says supported in v1; UI-SPEC says one input per param.
   - What's unclear: the metadata schema (`databases.{db}.queries.{name}.params`) doesn't carry types — Datasette's canned-query system is untyped. Submitting "abc" for an integer param produces a SQL error message handled by Pattern 4.
   - **RESOLVED:** ship `<input type="text">` only. Datasette's error message ("invalid input") renders as the friendly error block. Typed inputs are Phase 8 if requested. Implemented by Plan 06-05 `sql_db.html` template.

5. **Should the `/sql/{db}` results table use `<table>` or a `<div>`-based pseudo-table?**
   - What we know: UI-SPEC names a `.sql-results-table` class, harvest pattern `.api-table` baseline.
   - What's unclear: column-overflow on wide queries — `<table>` with `overflow-x: auto` parent.
   - **RESOLVED:** `<table class="sql-results-table">` inside `<div class="sql-results-wrap" style="overflow-x:auto; max-height:60vh; overflow-y:auto">`. Standard pattern. UI-checker accepts. Implemented by Plan 06-05 `sql_db.html` results block + Plan 06-06 CSS append for `.sql-results-wrap` / `.sql-results-table`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Frontend runtime | ✓ | 3.12.x in container | — |
| `httpx` 0.28.1 | Datasette HTTP client | ✓ (pinned) | 0.28.1 | — |
| `fastapi` 0.136.0 | Web framework | ✓ (pinned) | 0.136.0 | — |
| `jinja2` 3.1.6 | Templates | ✓ (pinned) | 3.1.6 | — |
| `pyyaml` 6.0.x | changelog loader | ✗ in pyproject.toml | (system has 6.0.3) | NONE — must be added |
| Live `zeeker-datasette` at `:8001` | All routes via httpx | ✓ | datasette 0.65.1 | None — frontend renders 503 if unreachable (Pitfall 10) |
| `datasette-search-all` plugin | ❌ NOT used | ✓ on Datasette side (HTML-only; bypassed) | v1.1.4 | N/A — D-03 avoids this dependency |

**Missing dependencies with no fallback:** `pyyaml` MUST be added to `packages/zeeker-frontend/pyproject.toml`. Plan adds a discrete task for this; otherwise Pitfall 12.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 + pytest-httpx 0.36.0 (pinned in `packages/zeeker-frontend/pyproject.toml`) |
| Config file | `packages/zeeker-frontend/pyproject.toml` `[tool.pytest.ini_options] asyncio_mode = "auto"` |
| Quick run command | `cd packages/zeeker-frontend && uv run pytest -x` |
| Targeted file | `cd packages/zeeker-frontend && uv run pytest tests/test_routes_aux.py -x` |
| Full suite command | `cd packages/zeeker-frontend && uv run pytest` (frontend) + `bash scripts/verify_phase_06.sh` (integration) + `bash scripts/verify_api_parity.sh` (parity gate) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-frontend-route-set | `/developers` returns 200 with rendered HTML | unit (TestClient + MockTransport) | `pytest tests/test_routes_aux.py::test_developers_renders -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/status` returns 200, includes 3 stats + timeline rows | unit | `pytest tests/test_routes_aux.py::test_status_renders -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/sources` returns 200, hides `_zeeker_*` tables | unit | `pytest tests/test_routes_aux.py::test_sources_hides_internal -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/about` returns 200, italic-accent H1 | unit | `pytest tests/test_routes_aux.py::test_about_renders -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/how-to-use` returns 200, no `/-/search` href leaks | unit | `pytest tests/test_routes_aux.py::test_how_to_use_re_pointed -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/llms.txt` returns 200 + `Content-Type: text/plain; charset=utf-8`, body starts with `# data.zeeker.sg` | unit | `pytest tests/test_routes_aux.py::test_llms_txt_format -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/robots.txt` returns 200 + `text/plain` | unit | `pytest tests/test_routes_aux.py::test_robots_txt -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/search` empty `q` renders State A (hero + tips, no fan-out) | unit | `pytest tests/test_routes_search.py::test_search_empty_query -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/search?q=DBS` fans out across `searchable_tables`, groups results | unit | `pytest tests/test_routes_search.py::test_search_groups_results -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/search` partial failure (one mocked-fail table) still renders successful groups | unit | `pytest tests/test_routes_search.py::test_search_partial_failure -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `/sql` landing lists databases | unit | `pytest tests/test_routes_sql.py::test_sql_landing -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `GET /sql/{db}` renders empty editor + canned-queries | unit | `pytest tests/test_routes_sql.py::test_sql_db_get -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `POST /sql/{db}` with valid SQL renders results | unit | `pytest tests/test_routes_sql.py::test_sql_db_post_success -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `POST /sql/{db}` with invalid SQL renders friendly error block (handles upstream HTTP 400) | unit | `pytest tests/test_routes_sql.py::test_sql_db_post_400_error -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `POST /sql/{db}` truncated=true renders banner | unit | `pytest tests/test_routes_sql.py::test_sql_db_truncation_banner -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `POST /sql/{db}` URL-encodes `sql` for export anchors | unit | `pytest tests/test_routes_sql.py::test_sql_db_export_links -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `discover_searchable_tables` extracts `fts_table` field, hides `_zeeker_*` and `hidden:true` | unit | `pytest tests/test_datasette_client_phase06.py::test_discover_searchable -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `execute_sql` builds `_param_<name>` URL params | unit | `pytest tests/test_datasette_client_phase06.py::test_execute_sql_params -x` | ❌ Wave 0 |
| REQ-frontend-route-set | `_detect_params` regex catches `:name` placeholders, dedupes | unit | `pytest tests/test_routes_sql.py::test_detect_params_regex -x` | ❌ Wave 0 |
| REQ-frontend-route-set | Changelog loader reads YAML, returns empty list on missing file | unit | `pytest tests/test_changelog.py::test_loader -x` | ❌ Wave 0 |
| REQ-eliminate-template-drift | All aux pages reference `/static/css/zeeker.css` (single design language) | integration | `bash scripts/verify_phase_06.sh` (positive grep) | ❌ Wave 0 |
| REQ-eliminate-template-drift | All aux pages render italic-accent `<h1>...<em>` | integration | `bash scripts/verify_phase_06.sh` | ❌ Wave 0 |
| REQ-eliminate-template-drift | No `zeeker-base.css` leak (datasette HTML fallthrough) | integration | `bash scripts/verify_phase_06.sh` (negative grep) | ❌ Wave 0 |
| REQ-eliminate-template-drift | Footer Search nav link → `/search` (not `/-/search`) | integration | `bash scripts/verify_phase_06.sh` | ❌ Wave 0 |
| REQ-frontend-data-via-http | No `import sqlite3` anywhere in `packages/zeeker-frontend/` | static | `! grep -rE 'import sqlite3' packages/zeeker-frontend/src/` | shell — no test file needed |
| REQ-frontend-data-via-http | All Phase-6 handlers use `request.app.state.http` (no module-level `httpx.AsyncClient()` constructed inside a handler) | static | `! grep -rE 'httpx\.AsyncClient\(\)' packages/zeeker-frontend/src/zeeker_frontend/routes_*.py` | shell |
| REQ-api-byte-parity | Phase 6 adds zero new `.json|.csv|.db|/-/` routes; baseline still clean | integration | `bash scripts/verify_api_parity.sh` (against `phase-03-pre/`) | ✅ exists |

### Sampling Rate

- **Per task commit:** `cd packages/zeeker-frontend && uv run pytest -x` (~5-10s expected for full frontend suite at this size).
- **Per wave merge:** Same + `bash scripts/verify_phase_06.sh` (smoke against running local containers).
- **Phase gate:** `bash scripts/verify_phase_06.sh` AND `bash scripts/verify_api_parity.sh` AND production smoke (`BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_06.sh`) before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `packages/zeeker-frontend/tests/test_routes_aux.py` — covers `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/robots.txt`
- [ ] `packages/zeeker-frontend/tests/test_routes_search.py` — covers `/search` State A + State B + partial-failure + 503 empty-cache + group sort + `<mark>` highlighting
- [ ] `packages/zeeker-frontend/tests/test_routes_sql.py` — covers `/sql` landing, `GET /sql/{db}`, `POST /sql/{db}` success/error/truncation paths, `_detect_params` regex
- [ ] `packages/zeeker-frontend/tests/test_datasette_client_phase06.py` — covers `discover_searchable_tables`, `search_table`, `execute_sql`
- [ ] `packages/zeeker-frontend/tests/test_changelog.py` — covers YAML loader + empty-list fallback
- [ ] `packages/zeeker-frontend/tests/fixtures/searchable_databases.json` + `headlines_search_results.json` — fixture for FTS fan-out tests (extend the existing fixtures pattern from Phase 5)
- [ ] `packages/zeeker-frontend/tests/fixtures/metadata_with_canned_queries.json` — fixture with a synthetic `databases.{db}.queries.foo = {sql: "SELECT :id", title: "Foo", params: ["id"]}`
- [ ] `packages/zeeker-frontend/tests/fixtures/sql_error_400.json` — body shape from a real Datasette 400 response (captured via `curl`)
- [ ] `scripts/verify_phase_06.sh` — integration verifier (extends Phase 4; re-runs Phase 5 inline; positive Phase-6 asserts)
- [ ] No new framework install — pytest, pytest-asyncio, pytest-httpx already pinned.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Site is public read-only; no auth in scope |
| V3 Session Management | no | No sessions; no cookies set by frontend Phase 6 |
| V4 Access Control | yes | Hidden-table predicate (`hidden` flag + `_zeeker_*` prefix) — D-15 carry-forward; applied to `/sources`, `/developers`, `/llms.txt`, `/sql` canned-queries |
| V5 Input Validation | yes | (1) Querystring allowlist on `/sql/{db}` form (only `sql` + `_sql_param_*` accepted); (2) `q` param to `/search` passed verbatim to Datasette (Datasette FTS5 escapes); (3) `db` and `table` path params constrained by FastAPI route patterns |
| V6 Cryptography | no | No crypto operations; HTTPS termination is Caddy's job (out of scope) |

### Known Threat Patterns for FastAPI/Jinja/Datasette

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via canned-query param substitution | Tampering | Use `_param_<name>=value` URL params, NOT string concatenation. Datasette binds via prepared-statement-style placeholders. `[CITED: docs.datasette.io/en/stable/sql_queries.html#named-parameters]` |
| SSRF via querystring smuggling | Tampering | Allowlist `ds_params` explicitly (Pattern 4 + Pitfall 7). NEVER `params=request.form()`. |
| HTML injection via `<mark>` highlighting on FTS results | Tampering | Jinja autoescape on `.html` (Phase 4 wired); only `|safe` filter would bypass — DON'T use it. `<mark>` markup MUST be added by Datasette server-side via `_search_highlight`, NOT by frontend regex on user input. |
| Internal hostname leak (`zeeker-datasette:8001`) into HTML | Information disclosure | Phase 5 Pitfall 2 mitigation already in place for `next_url`; Phase 6 routes don't pass `next_url` through, but verifier asserts `! grep zeeker-datasette:8001` on every aux page response. |
| Reflected XSS via `q` echoed in `/search` H1 | Tampering | Jinja autoescape — `<h1>Results for <em>{{ q }}</em></h1>` autoescapes `<` `>` `&`. Verifier curl `/search?q=<script>` and asserts no raw `<script>` in response body. |
| ms_limit DoS (long-running SQL) | DoS | Datasette enforces `ms_limit=3000` (D-08 trusts this). Frontend adds NO timeout layering — let Datasette terminate; render the 400 + error message via Pattern 4. |
| Row-cap DoS (1000-row response sucking RAM) | DoS | Datasette enforces 1000-row cap. Frontend renders `truncated=true` banner + CSV download link (suffix-routed direct, bypasses frontend memory). |
| `_zeeker_*` table disclosure via `/sql/{db}` arbitrary SQL | Information disclosure | NOT a defense layer — `/sql` is intentionally a SQL editor. `_zeeker_*` tables are filtered from listings/links but NOT from SELECT-able tables. Datasette read-only mode means worst case is metadata disclosure (which is already public elsewhere on the site). Documented acceptable risk. |

## Sources

### Primary (HIGH confidence)
- **Live datasette container probes** (`/-/databases.json`, `/sglawwatch.json`, `/sglawwatch.json?sql=…`, `/sglawwatch/headlines.json?_search=…`, `/-/metadata.json`, `/-/search.json`, `/-/plugins.json`) — verified response shapes, status codes, and field semantics on 2026-04-25.
- **`packages/zeeker-frontend/pyproject.toml`** — pinned versions for fastapi, httpx, jinja2, pytest, pytest-asyncio, pytest-httpx.
- **Phase 4 + 5 SUMMARY files** (`.planning/phases/04-port-home-database-pages/04-04-SUMMARY.md`, `.planning/phases/05-port-table-browse-row-view/05-01-SUMMARY.md`, `05-05-SUMMARY.md`) — established patterns: lifespan, `app.state.http`, querystring allowlist, hidden-table predicate, Cache-Control values, verifier composition.
- **M1 source code** (`plugins/developers_page.py`, `plugins/status_page.py`, `plugins/sources_page.py`, `plugins/strings.yaml`, `templates/pages/*.html`, `static/css/zeeker-base.css`) — canonical data shapes and CSS subsection harvest sources.
- **Datasette docs** — JSON API conventions (`/-/databases.json`, `_shape=objects`, `_search`, named parameters), read-only mode, `ms_limit`, 1000-row cap, canned queries metadata path. `[CITED: docs.datasette.io/en/stable/json_api.html]` `[CITED: docs.datasette.io/en/stable/sql_queries.html]`
- **Python 3 stdlib docs** — `asyncio.gather(return_exceptions=True)` semantics; `asyncio.TaskGroup` cancellation behavior. `[CITED: docs.python.org/3/library/asyncio-task.html]`
- **FastAPI docs** — route registration order, `Form()` body parsing, `PlainTextResponse`, `FileResponse`. `[CITED: fastapi.tiangolo.com/]`

### Secondary (MEDIUM confidence)
- **`scripts/verify_phase_05.sh`** — verifier composition pattern; section M provides the exact assertions Phase 6 must flip.
- **`.planning/notes/datasette-styling-limits.md`** — informs why we port (not patch) and why Phase 7 deletes M1 templates.
- **UI-SPEC §CSS Harvest** — line numbers in `static/css/zeeker-base.css` for each subsection. Cross-checked against the file directly: `.timeline` at 2713 (UI-SPEC said 2713-2779 — confirmed); `.method-card` at 812 (UI-SPEC said 805-825 — confirmed); `.api-table` at 2802+ (confirmed). Line numbers will drift slightly during the harvest if the CSS is modified concurrently — executor verifies during the actual port.

### Tertiary (LOW confidence — flagged for validation)
- **`pyyaml>=6.0,<7.0`** version bound — `[ASSUMED]` based on training; executor verifies latest stable at install time.
- **`/llms.txt` legacy `/-/search.json` reference** — should it stay or get re-pointed to `/search.json`? `[ASSUMED]` keep verbatim 1:1 with M1 (LLM consumers may have ingested the URL pattern). Open Question 3 (this section) addresses re-pointing for human-facing surfaces only.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep pinned in `pyproject.toml`; `pyyaml` is the one new addition with `[ASSUMED]` version pin verified at install time.
- Architecture: HIGH — patterns inherited verbatim from Phase 4-5; live-verified response shapes for the only new mechanics (`fts_table` field, SQL 400 body, `/-/metadata.json` queries path).
- Pitfalls: HIGH — 13 pitfalls catalogued; 10 are derived from live probes or Phase 4-5 carry-forward; 3 are framework semantic gotchas confirmed against current Python / FastAPI / Jinja docs.
- Validation Architecture: HIGH — test framework already wired in Phase 2; conftest fixtures already extant; only new test files + new fixtures gap.
- Security Domain: HIGH — site is public read-only; threat model is well-understood (FastAPI/Jinja/Datasette stack with no auth); STRIDE table covers the realistic attack surface.

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days — stack is stable; only risk is pyyaml release between now and merge, which is low and verified at install time).

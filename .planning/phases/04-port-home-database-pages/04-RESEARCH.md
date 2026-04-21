# Phase 4: Port home + database pages — Research

**Researched:** 2026-04-22
**Domain:** FastAPI + Jinja2 + httpx port of Datasette-rendered HTML templates; Caddy-routed static asset serving; first production deploy of the M2 split
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from 04-CONTEXT.md)

### Locked Decisions

**Phase boundary — what this phase ships:**
- Only two FastAPI HTML routes: `GET /` (home) and `GET /{db}` (database overview)
- First production deploy of the new frontend HTML path under `data.zeeker.sg` via Caddy's `else → frontend` catch-all
- Does NOT port `/{db}/{table}`, `/{db}/{table}/{pk}` (Phase 5), auxiliary pages (Phase 6), or delete M1 from `packages/zeeker-datasette/` (Phase 7)

**Template location & organization (locked):**
- `packages/zeeker-frontend/src/zeeker_frontend/templates/` holds all Jinja
- `base.html` = shared shell chrome (combines M1's `_header.html` + `_footer.html`); page templates extend it via Jinja `{% block %}`
- Page templates: `index.html`, `database.html`
- `_partials/` folder for small reusable chunks (start flat; add hierarchy only when needed)
- Static under `packages/zeeker-frontend/src/zeeker_frontend/static/` with `css/zeeker.css` (single file) + `fonts/` (self-hosted woff2)
- **DO NOT wildcard-copy all of M1's `static/`.** Harvest only what home + database + shell need

**Data-access contract (locked):**
- Frontend reads EXCLUSIVELY via HTTP from `http://zeeker-datasette:8001/...json` (DEC-5, REQ-frontend-data-via-http). No SQLite, no volume mount.
- Home page uses `GET /.json` (+ optionally `GET /-/metadata.json`)
- Database page uses `GET /{db}.json`
- Filter hidden tables (`_zeeker_*`, FTS internals) by trusting Datasette's `hidden: true` flag (verified — it covers both categories)
- In-memory TTL cache on metadata endpoints, TTL seconds-to-minutes
- 4xx from datasette → proxy status to user; 5xx/timeout → graceful error page

**FastAPI route handler pattern (locked):**
- `@asynccontextmanager` lifespan + `app.state.http = httpx.AsyncClient(...)` for connection reuse
- Handlers thin: HTTP fetch → assemble template context → render
- Response headers: `Cache-Control: public, max-age=60, stale-while-revalidate=300` on `/` and `/{db}`
- If `/{db}` doesn't exist in `/.json`, raise 404

**CSS harvest strategy (locked):**
- Harvest only theme + shell + home + database sections from M1's `static/css/zeeker-base.css` (4116 lines total)
- LEAVE OUT: feed cards (Phase 5), row reading layout (Phase 5), auxiliary page styles (Phase 6)
- Target: `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` (~2500 lines; not load-bearing)
- **Zero design changes.** If a harvest looks off, fix the harvest, not the design

**Nav behavior (locked):**
- Home + database (Phase 4) → frontend nav
- Table, row, auxiliary (Phase 5-6) → frontend nav (once they land)
- `/-/sql`, `/-/versions.json` etc. → datasette's default HTML, no frontend nav (acceptable — dev surfaces)

**Static-asset routing (locked to current Caddyfile):**
- `/static/*.css`, `/static/fonts/*.woff2` → frontend via catch-all (suffix `.css`/`.woff2` not in `*.json|*.csv|*.db|/-/*` list)
- No Caddyfile edits expected; verify in practice

**Production deploy (locked):**
- Pre-deploy smoke check: `verify_phase_04.sh` against production BEFORE advertising
- Rollback: `git revert` the compose/deploy commit, then `docker compose up -d --build`
- `docker-compose.prod.yml` likely needs to be authored this phase (does not exist today)
- Domain: `data.zeeker.sg`; Caddy auto-HTTPS handles TLS

### Claude's Discretion
- Exact httpx client configuration (timeouts, pool size) — use sensible defaults
- Jinja2 `extends`/`block` vs. `include` — prefer `extends` for base (matches M1 pattern)
- Pydantic models for Datasette payloads — use where type safety is cheap (tables list); skip for site metadata
- Adding frontend dependencies beyond FastAPI/httpx/jinja2 — prefer NO; justify if added

### Deferred Ideas (OUT OF SCOPE)
- `/favicon.ico`, `/robots.txt`, `/apple-touch-icon.png` — include if trivial, else Phase 8
- Real-time database stats — use cached metadata, full real-time = Phase 8
- Mobile-first CSS audit beyond M1 — M1 responsive collapses are inherited
- A11y audit beyond M1 semantics — follow-up phase
- Table browse + row view — Phase 5
- Auxiliary pages — Phase 6
- Datasette package cleanup — Phase 7
- Matomo + overlay decision — Phase 8
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-frontend-route-set | Frontend FastAPI service serves `/`, `/{db}`, ... (full set built across phases 4-6) | Phase 4 ships `/` + `/{db}`. Exact Datasette JSON contract for both is enumerated below (§"Datasette JSON API Contract"). FastAPI route handlers specified in §"Architecture Patterns / Pattern 1". |
| REQ-eliminate-template-drift | Single frontend codebase owns all HTML — no V1/V2 drift, no co-existing eras | Jinja-binding port map (§"Jinja Template Binding Port Map") enumerates every Datasette-specific context variable in M1's 4 target templates and its FastAPI replacement. Harvest source + target table pins each file's destination. |
| REQ-frontend-data-via-http | Frontend reads data exclusively via internal HTTP; no direct SQLite | httpx.AsyncClient + lifespan pattern locked (§"Pattern 1"). Dockerfile inherits Phase-2 discipline (no sqlite client, no data volume). |

</phase_requirements>

## Summary

Phase 4 is a well-scoped structural port. The design contract is LOCKED in the `sketch-findings-zeeker-datasette` skill, the data-access contract is LOCKED as "HTTP only from `http://zeeker-datasette:8001`", and the two target templates (`templates/index.html` 183 lines, `templates/database.html` 241 lines) are narrow enough that the Jinja binding surface can be fully enumerated — which this research does below.

The Datasette JSON API gives us exactly what M1 was already using via Datasette's template context: `/.json` returns a dict of databases keyed by name with `tables_count`, `hash`, `path`, etc.; `/{db}.json` returns `{database, size, tables, views, queries, source, source_url, license, license_url, hidden_count, ...}` where each `tables[]` entry has the exact fields M1's `database.html` reads (`name`, `columns`, `primary_keys`, `count`, `hidden`, `fts_table`). Critically, **Datasette's `hidden: true` flag already covers both `_zeeker_*` tables and FTS internals** — so filtering is `if not t["hidden"]`, not a string-prefix check. Per-DB titles/descriptions come from `/-/metadata.json` under `databases.{name}`; there's a wildcard `*` key that must be excluded.

The Jinja binding port is also narrow: M1's templates use four Datasette-specific additions — the `s()` / `plural()` helpers from `string_manager.py`, the `filesizeformat` filter from `template_filters.py`, the `{% extends "default:index.html" %}` default-template chain, and a `current_year` context var injected by `string_manager`'s `extra_template_vars` hook. All four have straightforward replacements: inline the strings (strings.yaml is under-used — only 15 keys appear in phase-4 templates, half already have literal defaults), register the three custom filters as a small `filters.py` module in the frontend, replace `{% extends "default:..." %}` with `{% extends "base.html" %}`, and inject `current_year` at render time from `datetime.now().year`.

The CSS harvest is mechanical: M1's `static/css/zeeker-base.css` has **explicit banner comment delimiters** (`/* =========== SHELL CHROME — phase 01 ============ */` etc.) — the relevant Phase-4 sections are lines **1-163 (fonts + tokens + base body/link styles)**, **3164-3568 (shell chrome)**, **3568-3723 (home)**, **3724-3862 (database editorial rows)**, and **4097-4116 (tail `footer a:link` cascade override)**. Total ~2,300 lines of the 4,116, confirming the ~60% target.

**Primary recommendation:** Split planning into five atomic plans:
1. **04-01 Scaffold + base template** — `base.html`, `main.py` additions (lifespan, mount static, TemplateResponse plumbing), deps, no route logic yet
2. **04-02 CSS + fonts harvest** — copy fonts, extract the 5 identified CSS ranges into `zeeker.css`, rewrite the three `@font-face url()` paths (they use `/static/fonts/inter-latin.woff2` — unchanged after the port since Caddy catch-all routes `/static/*` to frontend)
3. **04-03 Home route + template** — `GET /` handler + `index.html`, including the Jinja-binding port map (replace `s()`, `plural()`, `filesizeformat`)
4. **04-04 Database route + template** — `GET /{db}` handler + `database.html`, including 404 handling + hidden-table filter verification
5. **04-05 Production deploy overlay + verifier + smoke** — `docker-compose.prod.yml`, `verify_phase_04.sh`, capture post-deploy `phase-04-pre` baseline for Phase-5 parity reference

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTML rendering (`/`, `/{db}`) | Frontend Server (FastAPI/Jinja) | — | Phase 4 is the definitional scope. All HTML moves out of Datasette. |
| Data retrieval (metadata + row counts) | API / Backend (Datasette) | Frontend (httpx client) | DEC-5 locked: only Datasette touches SQLite; frontend reads via HTTP. |
| Static asset delivery (CSS, fonts) | Frontend Server (StaticFiles mount) | CDN (Caddy catch-all) | Caddy routes `/static/*` (no suffix match) to frontend; frontend serves via `StaticFiles`. |
| TLS termination | CDN (Caddy) | — | Caddy auto-HTTPS. Frontend/Datasette don't see TLS. |
| URL routing (API vs HTML) | CDN (Caddy) | — | Phase-3 Caddyfile is load-bearing; this phase does not touch it. |
| Caching (metadata) | Frontend Server (in-memory TTL) | API (Cache-Control header) | Datasette already sets `Cache-Control: public, max-age=300, s-maxage=3600` on `/.json`; frontend adds its own TTL cache. |
| Error pages (404 / 5xx) | Frontend Server | — | `/{db}` that doesn't exist → 404 from FastAPI; datasette 5xx → frontend graceful page. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | `0.136.0` (already pinned) | Route handlers, lifespan, request/response | [VERIFIED: packages/zeeker-frontend/pyproject.toml] Pinned in Phase 2. `fastapi[standard]` extra pulls uvicorn + jinja2 + httpx via Starlette transitively but we pin explicitly. |
| Jinja2 | `3.1.6` (already pinned) | HTML templates | [VERIFIED: pyproject.toml] Pinned. Starlette's `Jinja2Templates` wraps it. |
| httpx | `0.28.1` (already pinned) | Async HTTP client to Datasette | [VERIFIED: pyproject.toml] Pinned. `httpx.AsyncClient` with connection pooling is the canonical FastAPI pattern [CITED: fastapi.tiangolo.com/advanced/events]. |
| uvicorn | `0.44.0` (already pinned) | ASGI server | [VERIFIED: pyproject.toml] Pinned. Used in Dockerfile CMD. |
| python-multipart | (transitive via fastapi[standard]) | Form parsing | Optional — only if we later add forms. Not needed for Phase 4's read-only routes. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `cachetools` (stdlib alternative: `functools.lru_cache` + timestamp) | `cachetools==5.x` if added | TTL cache for `/.json` response | [ASSUMED] Not currently in pyproject.toml. If added: "cachetools 5.3.x" is the standard Python in-memory TTL cache. Alternative: roll a 20-line `TTLCache` dict with `time.monotonic()` — avoids a new dep. **Recommendation: roll the 20-line cache.** The cache use is narrow (one or two keys) and adding a dep for it violates the "prefer NO new deps" discretion note. |

No new deps strictly required. The dep count stays at 4 runtime packages.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@asynccontextmanager` lifespan | Deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` | Lifespan is the recommended replacement [CITED: fastapi.tiangolo.com/advanced/events]. Do not use the old events. |
| `httpx.AsyncClient` on `app.state` | A new client per request | Per-request clients kill connection pooling and add 2-5ms per request. [CITED: fastapi.tiangolo.com best-practice pattern via Context7]. |
| `Jinja2Templates(directory=...)` | Manual `Environment` construction | Starlette's `Jinja2Templates` auto-enables `select_autoescape()` for `.html`/`.htm`/`.xml` [CITED: starlette.dev/templates]. Manual Environment construction is an XSS footgun if you forget to set `autoescape=True`. |
| `cachetools.TTLCache` | Hand-rolled dict + monotonic timestamp | Both work; hand-rolled saves a dep. |
| `Pydantic` models for all Datasette payloads | Plain dicts passed to templates | Pydantic buys type safety + validation but costs schema-drift maintenance. Tables list is worth typing; site metadata is a pass-through. Use `TypedDict` as a middle ground if typing wanted without runtime validation. |

**Installation:**

```bash
# No new packages needed. Existing pyproject.toml covers everything.
cd packages/zeeker-frontend && uv sync
```

**Version verification (npm registry equivalent = PyPI):**

[VERIFIED: `pip index versions` or PyPI] As of 2026-04-22:
- `fastapi==0.136.0` — pinned, current at phase start (Phase 2). Current latest per PyPI is 0.136.0. No upgrade needed.
- `jinja2==3.1.6` — pinned. 3.1.6 is current stable.
- `httpx==0.28.1` — pinned. 0.28.x line is current; 0.29 is beta.
- `uvicorn==0.44.0` — pinned, current.

No version bumps required. All pins were set in Phase 2 and remain current. If a downstream plan wants to bump anything, justify it against a specific need.

## Architecture Patterns

### System Architecture Diagram

```
Browser / curl
      |
      v
   Caddy :80/:443  (Phase-3 Caddyfile — suffix routing)
      |
      +-- @datasette (*.json | *.csv | *.db | /-/*)  ----> zeeker-datasette:8001 (Datasette, unchanged)
      |                                                          |
      |                                                          v
      |                                                    /data/*.sqlite3  (read-only, S3-downloaded)
      |
      +-- catch-all (everything else)                 ----> frontend:8000 (FastAPI, Phase 4)
                                                              |
                                                              +-- GET /                 -->  render index.html
                                                              |      |
                                                              |      +-- httpx GET http://zeeker-datasette:8001/.json
                                                              |      +-- (optional) httpx GET /-/metadata.json
                                                              |
                                                              +-- GET /{db}             -->  render database.html
                                                              |      |
                                                              |      +-- httpx GET http://zeeker-datasette:8001/{db}.json
                                                              |      +-- if 404 -> raise HTTPException(404)
                                                              |
                                                              +-- GET /static/*         -->  StaticFiles mount (css, fonts)
                                                              |
                                                              +-- GET /frontend-test    -->  JSON (Phase-2 healthcheck target)
                                                              |
                                                              +-- everything else       -->  404 (Phases 5-6 will add routes)
```

Arrows show request flow. The frontend never touches SQLite directly; httpx is the sole data-access path.

### Recommended Project Structure

```
packages/zeeker-frontend/
├── Dockerfile                                  # Phase-2 baseline (no change Phase 4)
├── pyproject.toml                              # no new deps; may bump nothing
├── README.md
├── uv.lock
├── src/zeeker_frontend/
│   ├── __init__.py
│   ├── main.py                                 # Phase 4: add lifespan, mount, routes
│   ├── datasette_client.py                     # NEW — thin httpx wrapper + TTL cache
│   ├── filters.py                              # NEW — pluralize, safe_format, filesizeformat
│   ├── templates/
│   │   ├── base.html                           # NEW — combines _header + _footer with blocks
│   │   ├── index.html                          # NEW — ported from M1 templates/index.html
│   │   └── database.html                       # NEW — ported from M1 templates/database.html
│   └── static/
│       ├── css/
│       │   └── zeeker.css                      # NEW — harvested from M1 zeeker-base.css
│       └── fonts/
│           ├── inter-latin.woff2               # NEW — copied from M1 static/fonts/
│           ├── jetbrains-mono-latin.woff2      # ditto
│           └── fraunces-latin.woff2            # ditto
└── tests/
    └── (pytest — existing Phase-2 placeholder)
```

### Pattern 1: FastAPI Lifespan + Shared httpx Client

**What:** Initialize `httpx.AsyncClient` once at startup, stash on `app.state`, reuse across all requests, close at shutdown. This is the FastAPI-canonical pattern for 2026.

**When to use:** Any FastAPI app that makes outbound HTTP calls. Mandatory for Phase 4 per CONTEXT.md.

**Example:**

```python
# Source: fastapi.tiangolo.com/advanced/events (Context7 /websites/fastapi_tiangolo)
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

DATASETTE_URL = "http://zeeker-datasette:8001"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connection pool with defaults; Datasette is internal so latency is low.
    # timeout: total seconds; http2: False because uvicorn on HTTP/1.1 internal net is fine
    app.state.http = httpx.AsyncClient(
        base_url=DATASETTE_URL,
        timeout=httpx.Timeout(10.0, connect=2.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    yield
    await app.state.http.aclose()


app = FastAPI(title="zeeker-frontend", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/zeeker_frontend/static"), name="static")
templates = Jinja2Templates(directory="src/zeeker_frontend/templates")
# Register custom filters (see Pattern 3 below)
from zeeker_frontend import filters as zfilters
templates.env.filters["pluralize"] = zfilters.pluralize
templates.env.filters["safe_format"] = zfilters.safe_format
# NOTE: Jinja2 ships filesizeformat as a Flask filter, NOT by default — we must add it.
templates.env.filters["filesizeformat"] = zfilters.filesizeformat
```

**Timeout rationale:** Internal Docker bridge latency is < 5ms; 10s total with 2s connect is generous enough to cover a datasette S3-download-blocked boot window if a restart happens mid-traffic. Not a rigid requirement; tune if production shows otherwise.

**Pool size rationale:** 20 max connections on a single frontend worker handling home + database page GETs is over-provisioned; keeps headroom for Phase 5/6 when more routes land. Keepalive at 10 means normal load reuses a small pool.

### Pattern 2: Thin Handler + Graceful Error

**What:** Route handler does one httpx fetch, minimal shaping, render TemplateResponse. Do NOT duplicate Datasette's metadata-merging logic.

**When to use:** Every Phase-4 HTML handler.

**Example:**

```python
# /: home page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    client: httpx.AsyncClient = request.app.state.http
    try:
        r = await client.get("/.json")
        r.raise_for_status()
    except httpx.HTTPError:
        # Render an error page or raise 503; CONTEXT says "graceful error page"
        raise HTTPException(status_code=503, detail="Data API unavailable")

    raw = r.json()
    # Datasette returns {db_name: {name, hash, color, path, tables_count, table_rows_sum, views_count, ...}, ...}
    # Normalize to a list of dicts so Jinja iteration is cleaner.
    databases = [{"name": k, **v} for k, v in raw.items()]
    # Datasette has no "hidden database" concept today, but defensive filter doesn't hurt:
    visible_dbs = [d for d in databases if not d.get("hidden")]

    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "databases": visible_dbs,
            "stats": {"db_count": len(visible_dbs)},
            "current_year": datetime.now().year,
            # metadata passed through for hero description/license fallbacks (see Pattern 3)
            "metadata": await _fetch_site_metadata(client),
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


# /{db}: database page
@app.get("/{db}", response_class=HTMLResponse)
async def database(request: Request, db: str):
    client: httpx.AsyncClient = request.app.state.http
    r = await client.get(f"/{db}.json")
    if r.status_code == 404:
        raise HTTPException(404, detail="Database not found")
    r.raise_for_status()
    payload = r.json()

    # Datasette already marks _zeeker_* and FTS internals as hidden=true (verified live).
    # Trust it. No string-prefix check needed.
    visible_tables = [t for t in payload.get("tables", []) if not t.get("hidden")]

    # Per-DB title/description come from /-/metadata.json (NOT /{db}.json top-level).
    site_metadata = await _fetch_site_metadata(client)
    db_metadata = (site_metadata.get("databases", {}) or {}).get(db, {}) or {}

    response = templates.TemplateResponse(
        "database.html",
        {
            "request": request,
            "database": db,
            "tables": visible_tables,
            "views": payload.get("views", []),
            "canned_queries": payload.get("queries", []),
            "size": payload.get("size"),
            # Merge: top-level datasette merge gives source/license; db-level metadata has title/description
            "metadata": {
                **db_metadata,
                "source": payload.get("source"),
                "source_url": payload.get("source_url"),
                "license": payload.get("license"),
                "license_url": payload.get("license_url"),
            },
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

**Note on `_fetch_site_metadata`:** Wrap this in a TTL cache (60s) so we don't refetch `/-/metadata.json` on every home/database hit. Metadata drifts only when the datasette container rebuilds, so a minute of staleness is fine.

### Pattern 3: Custom Jinja Filters (Port of M1's Datasette Plugin Filters)

**What:** M1's `plugins/template_filters.py` registers 4 custom filters via Datasette's `prepare_jinja2_environment` hook. Phase 4 templates use 3 of these directly (`filesizeformat` — 3 occurrences; `pluralize`/`safe_format` — not used in phase-4 templates but used by phase 5/6 so may as well port now).

**When to use:** Once at app init, after `Jinja2Templates` construction.

**Example:**

```python
# packages/zeeker-frontend/src/zeeker_frontend/filters.py
"""Custom Jinja filters ported from M1's plugins/template_filters.py.

Only filesizeformat is strictly needed for Phase 4 (home hero + database hero
use `size|filesizeformat`). pluralize + safe_format are ported here too so
Phase 5/6 templates can rely on them without another migration round.
"""
from jinja2 import Undefined


def filesizeformat(value) -> str:
    """Bytes → human-readable (matches M1 behavior exactly)."""
    if isinstance(value, Undefined) or value is None:
        return "—"
    try:
        b = float(value)
    except (ValueError, TypeError):
        return str(value)
    if b < 1024:
        return f"{b:.0f} bytes"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:
        return f"{b / (1024 ** 2):.1f} MB"
    return f"{b / (1024 ** 3):.1f} GB"


def pluralize(value, arg: str = "s") -> str:
    """{{ count }} item{{ count|pluralize }} — ports M1 behavior verbatim."""
    try:
        n = int(value) if value is not None else 0
    except (ValueError, TypeError):
        n = 0
    if "," not in str(arg):
        return "" if n == 1 else str(arg)
    plural, singular = str(arg).split(",", 1)
    return singular.strip() if n == 1 else plural.strip()


def safe_format(value, format_string: str = "{:,}") -> str:
    """Safely format numbers, returning '—' on undefined."""
    if isinstance(value, Undefined) or value is None:
        return "—"
    try:
        if isinstance(value, str):
            value = int(value) if value.isdigit() else float(value)
        return format_string.format(value)
    except (ValueError, TypeError):
        return str(value) if not isinstance(value, Undefined) else "—"
```

Register in `main.py` immediately after `templates = Jinja2Templates(...)`.

### Anti-Patterns to Avoid

- **Creating an `httpx.AsyncClient` per request.** Kills connection pooling. Silently slower. [VERIFIED: httpx docs, FastAPI best practices via WebSearch]
- **Manually constructing a `jinja2.Environment` without `autoescape=select_autoescape()`.** XSS footgun. Use Starlette's `Jinja2Templates(directory=...)` which enables autoescape for `.html`/`.htm`/`.xml` by default. [CITED: starlette.dev/templates]
- **Filtering hidden tables with a string prefix check.** `t.name.startswith('_zeeker_')` misses FTS internals (`headlines_fts`, `*_fts_data`, `*_fts_docsize`, etc.). Datasette's `hidden: true` covers both categories — trust it. [VERIFIED: curl http://localhost/sglawwatch.json 2026-04-22]
- **Using the `*` wildcard key from `metadata.databases`.** That's Datasette's wildcard metadata applied to all databases; iterating it as if it were a real database causes a nonsense card. Filter: `{k: v for k, v in meta["databases"].items() if k != "*"}`. [VERIFIED: curl http://localhost/-/metadata.json 2026-04-22]
- **Porting the `s()` / `plural()` helpers without strings.yaml.** The strings.yaml only has 50 keys, and 15 are used in phase-4 templates — but only 8 of the 15 have YAML entries; the rest fall through to the literal default argument. Honest shortcut: inline the defaults directly in the Jinja template (they're already the defaults). Revisit `s()` if Phase 6 shows a genuine i18n need.
- **Touching `{% extends "default:..." %}` paths.** Datasette's `default:` prefix loads its built-in templates; FastAPI's Jinja has no such concept. Base template must be `{% extends "base.html" %}` and `base.html` must be fully self-contained.
- **Forgetting `{{ request }}` in TemplateResponse context.** Starlette's `Jinja2Templates` requires it; omitting raises `KeyError: request` at render time.
- **Adding cache-busting on first port.** Defer. Browsers Cache-Control the CSS at 60s max-age anyway. [ASSUMED: a font-rotation or palette change every few months is rare enough that a manual `?v=2` bump when needed is acceptable.]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML escaping | Manual `.replace("<", "&lt;")` | Jinja2 autoescape via `Jinja2Templates(directory=...)` | Starlette wraps Jinja with `select_autoescape()` [CITED: starlette.dev/templates]; handles edge cases (attribute vs text context). |
| HTTP connection pooling | Raw `socket` + connection reuse logic | `httpx.AsyncClient` with `limits=Limits(...)` | httpx handles DNS caching, keep-alive, HTTP/1.1 pipelining, retries-on-connection-reset — all battle-tested. |
| Pluralization logic | In-template `{% if n == 1 %}row{% else %}rows{% endif %}` scattered everywhere | Single Jinja `pluralize` filter (ported from M1) | M1 already made this decision; porting preserves template parity and keeps a single place to fix bugs. |
| File size formatting | In-template `{{ (size / 1024) | round(1) }} KB` | `filesizeformat` filter | Matches M1 output; future-proof for PB/TB. |
| Template path resolution | `open(f"templates/{name}.html").read()` | `Jinja2Templates(directory=...)` + `templates.TemplateResponse(...)` | Handles inheritance, caching, autoescape, `{% extends %}`, etc. |
| Static file serving | Custom `@app.get("/static/{path:path}")` handler | `app.mount("/static", StaticFiles(directory=...))` | StaticFiles handles MIME types, If-Modified-Since, range requests, security (path traversal). |
| Cache-Control headers | Manual middleware | Per-response `response.headers["Cache-Control"] = ...` | Phase 4 only has 2 cached routes. Middleware is overkill. |
| TTL cache on metadata | A global dict + manual TTL checks on every request | Small 20-line class with `time.monotonic()` | cachetools is a perfectly good library but it's ONE dep for ONE use — weigh dep cost. |
| 404/500 HTML pages | Custom error HTML | FastAPI's default JSON error responses (for now) + optional Jinja template handler in Phase 6 | Phase 4 CONTEXT only requires "graceful error page"; FastAPI's JSON `{"detail":"Not Found"}` is already served. Richer HTML error pages = Phase 6. |

**Key insight:** The Datasette-side API is doing the real work — schema introspection, SQL execution, metadata merging. The frontend's job is thin: one HTTP call, one template render. Every line of custom logic in the frontend is a line that duplicates Datasette's behavior and drifts from it over time.

## Datasette JSON API Contract

**VERIFIED live 2026-04-22** against the running production-shape stack (`docker compose ps` shows all healthy; `curl http://localhost/.json` through Caddy).

### `GET /.json` — home page data source

Returns an object, keyed by database name. Each value describes one attached database.

```json
{
  "sglawwatch": {
    "name": "sglawwatch",
    "hash": null,
    "color": "95ccde",
    "path": "/sglawwatch",
    "tables_and_views_truncated": [ /* up to 5 table summaries, truncated */ ],
    "tables_and_views_more": false,
    "tables_count": 2,
    "table_rows_sum": 0,
    "show_table_row_counts": false,
    "hidden_table_rows_sum": 0,
    "hidden_tables_count": 21,
    "views_count": 0,
    "private": false
  },
  "zeeker-judgements": { ... },
  "sg-gov-newsrooms": { ... }
}
```

**Fields Phase 4 uses:**

| Field | Type | Home template usage |
|-------|------|---------------------|
| `name` | str | Card anchor href (`/{{ db.name }}`), card title fallback (title-cased + hyphens→spaces) |
| `tables_count` | int | Per-card meta row ("N tables"), per-card big count, stat-band aggregation (`sum(d.tables_count for d in dbs)`) |
| `color` | str (hex without `#`) | **Not used in Phase 4** (M1 ignores it; preserve that) |
| `hash` | str | **Not used** |
| `table_rows_sum` | int | **Not currently used by M1 hero** but available if the stat band wants a "total rows" cell. Note: only populated when `show_table_row_counts` is true — for sglawwatch it's 0 (false). **Do not use for the hero "total rows" stat** because it's conditionally present. |

**Size (`database.size` in bytes) is NOT in this endpoint.** M1's `templates/index.html` line 104 does `{% if database.size is defined and database.size %}` — and `database.size` is ALWAYS undefined in `/.json`. The M1 home card never actually renders a size — that `{% if %}` is always false. Port the same defensive conditional and let it stay false; do NOT introduce a per-DB size fetch. (If size is wanted later, one N extra `/{db}.json` fetch per database = Phase 8.)

**Response characteristics:**
- Status: 200 OK
- Headers: `Cache-Control: public, max-age=300, s-maxage=3600`, `CORS allow-origin: *`
- Size (3 databases): ~4.3 KB compressed
- Latency (local): ~40ms

### `GET /{db}.json` — database page data source

```json
{
  "database": "sglawwatch",
  "private": false,
  "path": "/sglawwatch",
  "size": 24666112,
  "tables": [
    {
      "name": "headlines",
      "columns": ["id", "category", "title", ...],
      "primary_keys": ["id"],
      "count": 665,
      "hidden": false,
      "fts_table": "headlines_fts",
      "foreign_keys": {"incoming": [], "outgoing": []},
      "private": false
    },
    /* ... including hidden tables where hidden=true ... */
  ],
  "hidden_count": 21,
  "views": [],
  "queries": [],
  "allow_execute_sql": true,
  "query_ms": 0.8,
  "source": "Singapore LawWatch",
  "source_url": "https://www.singaporelawwatch.sg/",
  "license": "CC-BY-4.0",
  "license_url": "https://creativecommons.org/licenses/by/4.0/"
}
```

**Fields Phase 4 uses:**

| Field | Type | `database.html` usage |
|-------|------|------------------------|
| `database` | str | URL segment + form action + export links (passed as `database` template var) |
| `size` | int (bytes) | Hero meta-col "Size" + stat-band "on disk" cell — via `filesizeformat` filter |
| `tables` | list[dict] | Main editorial-row list; filter by `.hidden == false` first |
| `tables[].name` | str | Row anchor text + `{{ database }}/{{ table.name }}` URL + CSV/JSON links |
| `tables[].count` | int or null | Right-aligned row count cell (`null` renders `—`) |
| `tables[].columns` | list[str] | Middle column preview (cap at 8, then `+N`) |
| `tables[].primary_keys` | list[str] | Highlight PKs in the column preview (`.pk` class) |
| `tables[].hidden` | bool | **Filter: drop if true.** This covers `_zeeker_*` AND FTS internals. |
| `tables[].fts_table` | str or null | If truthy, render the FTS badge |
| `views` | list[dict] | № 02 Views section (views render as editorial rows with `view.name`, `view.description`) |
| `queries` | list[dict] | № 03 Saved queries section (canned queries — `query.name`, `query.title`, `query.description`) |
| `source`, `source_url` | str | Hero meta-col "Source" link |
| `license`, `license_url` | str | Hero meta-col "Licence" link |

**Fields NOT in this endpoint (must fetch from `/-/metadata.json`):**
- `metadata.title` (DB-level friendly title) — needed for hero H1 italic split
- `metadata.description` (DB-level description) — needed for hero lede
- `metadata.tables[name].title` / `metadata.tables[name].description` — needed for per-table friendly titles in the editorial rows

**404 response:** Status 404, body `{"ok": false, "error": "Database not found", "status": 404, "title": null}` — JSON. FastAPI should catch `r.status_code == 404` and `raise HTTPException(404)` BEFORE parsing JSON as dict. Do NOT call `r.raise_for_status()` blindly since it raises on 4xx and we want to handle 404 as a distinct case.

**Response characteristics:**
- Status: 200 OK
- Headers: `Cache-Control: public, max-age=300, s-maxage=3600`, `CORS allow-origin: *`
- Size (sglawwatch): ~6.8 KB compressed
- Latency (local): ~24ms

### `GET /-/metadata.json` — site-wide and per-DB metadata

```json
{
  "title": "SG LawWatch",
  "description": "Singapore legal news ...",
  "license": "CC-BY-4.0",
  "license_url": "https://creativecommons.org/licenses/by/4.0/",
  "source": "Singapore LawWatch",
  "source_url": "https://www.singaporelawwatch.sg/",
  "about": "Providing free access to structured data ...",
  "about_url": "https://data.zeeker.sg/about",
  "databases": {
    "sg-gov-newsrooms": {
      "title": "SG Government Newsrooms",
      "description": "News and announcements ...",
      "tables": {
        "mlaw_news": {"title": "Ministry of Law News", "description": "Press releases ...", "columns": { ... }},
        "judiciary_news": { ... }
      }
    },
    "*": {
      "allow_sql": true,
      "allow_facet": true,
      "allow_download": true,
      "tables": {
        "_zeeker_schemas": {"hidden": true},
        "_zeeker_updates": {"hidden": true}
      }
    },
    "sglawwatch": {
      "title": "SG LawWatch",
      "description": "..."
    }
  },
  "plugins": { ... },
  "extra_css_urls": [ ... ],
  "extra_js_urls": [ ... ],
  "menu_links": [ ... ]
}
```

**Fields Phase 4 uses:**

| Field | Usage |
|-------|-------|
| `title` | Footer copyright |
| `description` | Home hero lede (fallback when not db-specific); home `<meta name="description">` |
| `license`, `source`, etc. | Home hero meta-col fallbacks |
| `databases.{name}.title` | Per-database card title, database page H1 (with italic-last-word split) |
| `databases.{name}.description` | Per-database card body; database page hero lede |
| `databases.{name}.tables.{name}.title` | Per-table friendly title in editorial rows |
| `databases.{name}.tables.{name}.description` | Per-table description in editorial rows |
| `menu_links` | Nav menu links (rendered in base.html; excludes href=`/`) |
| `extra_css_urls` / `extra_js_urls` | **Ignore.** These are datasette's overlay mechanism; the frontend controls its own assets via `base.html` `<link>` / `<script>` tags. |

**Filter `*` key from `databases`:** `{k: v for k, v in meta["databases"].items() if k != "*"}`. M1's index.html doesn't iterate metadata.databases by key (only does dict lookups `metadata.databases[database.name]`), so the `*` key is ignored by accident; the frontend handler should filter explicitly to be defensive.

**Caching strategy:** Metadata rarely changes (only on datasette rebuild). Frontend TTL = 60s is fine; `/-/metadata.json` is < 20KB so it's essentially free to fetch.

## Jinja Template Binding Port Map

M1's 4 phase-4-relevant templates (`index.html`, `database.html`, `_header.html`, `_footer.html`) use these Datasette-specific constructs. Each needs a port strategy.

| M1 construct | Frequency | What it does in M1 | Port strategy | Location of port |
|---|---|---|---|---|
| `{% extends "default:index.html" %}` | 1× (index.html line 1) | Extends Datasette's built-in index template | Replace with `{% extends "base.html" %}` — base.html implements the blocks below directly | index.html |
| `{% extends "default:database.html" %}` | 1× (database.html line 1) | Same for database page | Replace with `{% extends "base.html" %}` | database.html |
| `{% block extra_head %}` | 2× | Injects meta description in `<head>` | Jinja `{% block head %}` in base.html — renamed from `extra_head` for clarity (keep old name if preferred) | base.html |
| `{% block nav %}` | 2× | Renders the nav + breadcrumb | Inline into base.html directly. Breadcrumb is data-driven: `{% if breadcrumbs %}...{% endif %}` reads from the template context (set in each page template via `{% set breadcrumbs = [...] %}` BEFORE calling super's block, or passed in from the handler). **Recommendation: pass `breadcrumbs` from the route handler** — cleaner than in-template `{% set %}` |
| `{% block content %}` | 2× | The actual page body | Native Jinja block in base.html | base.html |
| `{% block footer %}` | 2× | Renders the footer | Inline into base.html directly (no per-page override in Phase 4; Phase 5/6 can add one if needed) | base.html |
| `{% include "_header.html" %}` | 2× | Pulls in the nav partial | Eliminate — base.html is now the single shell | base.html |
| `{% include "_footer.html" %}` | 2× | Pulls in the footer partial | Eliminate — base.html is now the single shell | base.html |
| `{{ s('key', 'default') }}` | 15× in index.html + 0 in database.html (checked via grep) | Calls string_manager plugin's `s()` helper | **Inline the default literal**, drop `s()`. If Phase 6 shows i18n need, re-add later. Alternative: port a no-op `s(key, default)` helper that returns default — zero-risk stub matching the plugin's fallback behavior. **Recommendation: stub `s()` that returns default** so templates don't need to be rewritten, makes Phase 6 i18n easier if wanted. | `filters.py` or `context_processors.py` |
| `{{ plural(n, 'sk', 'pk') }}` | 4× in index.html + 1× in database.html | string_manager's `plural()` helper — looks up singular/plural strings in strings.yaml | Stub as `plural(n, singular_key, plural_key)` that ignores the keys and returns a hardcoded lookup from a small `PLURALS` dict (or: inline `"databases" if n != 1 else "database"`). **Recommendation: stub helper with an inline `PLURALS = {"plural_table": "tables", "plural_tables": "tables", "plural_database": "databases", ...}` dict** — preserves call sites 1:1 | `filters.py` |
| `{% set visible_dbs = databases\|rejectattr('hidden')\|list %}` | 1× | Filter hidden dbs | Stays verbatim — `rejectattr` is Jinja built-in | index.html (unchanged) |
| `{{ current_year }}` | 1× (index.html) + 1× (_footer.html) | Injected by string_manager's `extra_template_vars` hook | Pass from route handler: `"current_year": datetime.now().year` | main.py handlers |
| `{% set ns = namespace(total_tables=0) %}` + accumulator | 1× (index.html) | Sum `tables_count` across visible DBs | Stays verbatim — Jinja native | index.html |
| `{{ "{:,}".format(n) }}` | 2× in index.html + 2× in database.html | Python str.format for thousands separators | Jinja supports Python str.format via `"{:,}".format(n)` natively — **stays verbatim** | both |
| `{{ "{:02d}".format(loop.index) }}` | 2× (index.html) + 4× (database.html) | Two-digit zero-padded loop number | Stays verbatim — Jinja native | both |
| `{{ size\|filesizeformat }}` | 1× (index.html, in `{% if %}` block that's always false) + 2× (database.html) | File size formatting — from `plugins/template_filters.py` | Port to `filters.py` and register. Jinja2 does NOT ship this filter by default (Flask's `flask.helpers.filesizeformat` is the typical source, but we're not on Flask). **Must add** | register in main.py after `Jinja2Templates(...)` |
| `{{ str\|replace('_',' ')\|title }}` | 3× (index.html + database.html) | Sentence-case DB/table names | Stays verbatim — Jinja native | both |
| `{{ db_title.rfind(' ') }}` / `{{ db_title[:idx] }}` | 1× (database.html) | Python string method calls in Jinja | Jinja supports method calls natively — stays verbatim | database.html |
| `{% if s is defined %}...{% else %}...{% endif %}` | 1× (_footer.html) | Defensive check for `s()` availability | Since we stub `s()` globally, it's always defined. Simplify: drop the `is defined` branch, keep only the true branch | base.html (in footer section) |
| `{{ str_site_title\|default('data.zeeker.sg', true) }}` | 1× (_header.html) | String from string_manager's context dump (`string_context = {f'str_{k}': v for k, v in STRINGS.items()}`) | Drop the `str_site_title` layer; hardcode `"data.zeeker.sg"` or fetch from `metadata.title` | base.html |
| `{{ metadata.menu_links }}` | 1× (_header.html) | Iterates datasette's menu_links metadata | Port verbatim — it's just `metadata.menu_links` (a list of dicts); frontend passes metadata to templates the same way | base.html |
| `{{ request.url }}` | **Not used** in phase-4 templates (verified earlier in M1 notes — BLK-01) | — | N/A — but FastAPI's `request.url` IS defined if needed later | — |
| `datasette.metadata(...)` or other Python function calls on the `datasette` object | **Not used** in phase-4 templates (verified via grep — 0 occurrences) | — | N/A | — |

**Net result:** Phase 4's Jinja port needs:
1. A base.html that inlines the 2 partials, defines 4 blocks (`head`, `nav`, `content`, `footer`)
2. A tiny `filters.py` with 3 filters (filesizeformat, pluralize, safe_format) + 2 helpers (`s`, `plural`)
3. A context-processor pattern (or direct handler assignment) that injects `current_year` and `metadata` on every render
4. Zero changes to the body of `index.html` / `database.html` beyond `{% extends "default:..." %}` → `{% extends "base.html" %}` and removing the `_header`/`_footer` includes

This is a ~80 line delta per page template, not a rewrite.

## CSS Harvest Strategy

M1's `static/css/zeeker-base.css` is **4,116 lines** (verified). The file has explicit banner comment delimiters that make mechanical extraction possible.

### Section map (confirmed via grep of banner markers)

| Line range | Section | Phase 4 fate |
|---|---|---|
| 1–163 | Header comment + font-faces + introductory custom properties | **HARVEST** — fonts + initial tokens |
| 164–192 | Custom properties (palette, spacing, radii, shadows, typography tokens) | **HARVEST — partial.** All token declarations in `:root` are load-bearing |
| 193–267 | Base typography (`h1`, `h2`, `body`, `html`, focus ring) | **HARVEST** |
| 268–353 | Italic-accent signature (`h1 em`, `h1 .und`) + global `a/a:link/a:visited` override | **HARVEST** |
| 354–550 | Legacy / misc selectors (`header-search`, `header-left`, accessibility utilities) | **Partial harvest** — keep `.visually-hidden`, drop the rest (unused in phase 4) |
| 551–2889 | Legacy V1 cards-era styles (`.hero-section`, `.stats-strip`, `.database-card`, table styles, query UI, etc.) | **DROP** — M1's old markup that the new templates replaced. The phase-1 summaries confirm these are dead. |
| 2890–3159 | Legacy / tail of V1 era | **DROP** |
| 3160–3567 | `/* =========== SHELL CHROME — phase 01 ============ */` (`.container`, `.db-nav`, `.db-crumb`, `.db-header`, `.db-statband`, `.db-toolbar`, `.cta`, `.cat-pill`, `.fts-badge`, `.site-footer`, `.section`, `.section-num`, `.section-head`, `.kicker`) | **HARVEST — all of it** |
| 3568–3723 | `/* =========== HOME — phase 01 ============ */` (`.home-header .hero-search`, `.cards`, `.card`, `.card:nth-child(3n+N)`, `.card .idx`, `.card-meta`, `.card-desc`, `.card-count`, `.chip`, `.chips`, `.how-grid`, `.how-item`) | **HARVEST — all of it** |
| 3724–3862 | `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` (`.list`, `.row`, `.row::before`, `.row .idx/.name-col/.name/.desc/.cols/.pk/.more/.count-col/.count/.label/.date-col`, `.db-header .meta-col dd.export-links`) | **HARVEST — all of it** |
| 3863–3985 | `/* =========== FEED CARDS — phase 01 ============ */` (`.va-feed`, `.va-citation`, etc.) | **DROP** — Phase 5 (table browse). `.cat-pill` is already in SHELL CHROME so category pills harvest via that section. |
| 3986–4096 | `/* =========== PHASE 01 POLISH FIXES — post-QA tweaks ============ */` | **Partial harvest** — selectively pick items. A few are home/database-relevant (item #6 `.row + 5` scope if any?), many target auxiliary pages. Audit one-by-one during harvest plan. |
| 4097–4116 | Tail `footer a:link` cascade override | **HARVEST** — must remain in last 20 lines to beat Datasette's app.css if any datasette-served HTML still exists. BUT: after Phase-3 routing, the frontend doesn't load datasette's app.css (it's frontend-rendered HTML, not datasette HTML), so this override may be obsolete. **Hypothesis: check if footer links need the override in the frontend-rendered context. If not, drop it.** [ASSUMED — needs verification during 04-02 harvest plan] |

**Total harvest:** approximately 1-163 + some of 164-550 + 3160-3862 + 4097-4116. Let's estimate: **~2,200–2,400 lines** into the new `zeeker.css`. Matches CONTEXT's ~2500-line target.

### Harvest mechanics

Three practical approaches:
1. **`sed -n '<start>,<end>p'` per section** — surgical, scriptable, reviewable as a diff. **Recommended.**
2. **Copy the whole file, then delete unwanted sections with Edit tool** — easier to visually review but large diff.
3. **Hand-transcribe** — unnecessarily slow, error-prone.

Example script (04-02 plan shell):

```bash
SRC=/path/to/zeeker-datasette/static/css/zeeker-base.css
DST=/path/to/packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css
{
  sed -n '1,163p'    "$SRC"    # fonts + header comment
  sed -n '164,350p'  "$SRC"    # tokens + base typography + italic-accent + link overrides
  echo ""
  sed -n '3160,3862p' "$SRC"   # shell chrome + home + database editorial rows
  echo ""
  sed -n '4097,4116p' "$SRC"   # tail footer link override
} > "$DST"
```

Then manually inspect:
- Do all `var(--…)` references resolve? (Grep `var(--` in the destination, cross-check against `:root` block.)
- Do `@media (max-width: ...)` rules survive intact? (Count `@media`.)
- Are braces balanced? (`grep -c '{' = grep -c '}'`.)

### Font path rewrite

`@font-face` declarations in lines 1-40 reference `/static/fonts/inter-latin.woff2` etc. After the port:
- Destination path is **still** `/static/fonts/inter-latin.woff2` because Caddy routes `/static/*` to the frontend, and the frontend mounts its static at `/static`. **No path rewrite needed.**
- Copy all 3 woff2 files from `static/fonts/` to `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/`.

### Known minor hazard: dead selectors

Phase-1 polish notes flagged ~40 dead selectors (e.g., `.tables-grid`, `.database-card`, `.view-card`). They live in the legacy lines 551–2889 which we're DROPPING entirely in the harvest, so this self-resolves. No post-harvest cleanup needed.

## Static-asset Routing via Caddy (verification)

Phase-3 Caddyfile matcher: `path *.json *.csv *.db` + `path /-/*` → datasette; everything else → frontend.

**Phase 4 static paths:**

| URL | Matcher? | Routes to | Expected |
|---|---|---|---|
| `/static/css/zeeker.css` | No (`.css` not in list, not `/-/`) | frontend | 200 from StaticFiles |
| `/static/fonts/inter-latin.woff2` | No (`.woff2` not in list) | frontend | 200 from StaticFiles |
| `/static/fonts/jetbrains-mono-latin.woff2` | No | frontend | 200 |
| `/static/fonts/fraunces-latin.woff2` | No | frontend | 200 |
| `/favicon.ico` | No | frontend | 404 (deferred) |
| `/robots.txt` | No | frontend | 404 (deferred) |

**Verified:** the current Caddyfile [VERIFIED: Caddyfile line 38-41] only claims suffix globs `.json .csv .db` plus prefix `/-/*`. `.css`, `.woff2`, `.ico` are free.

**Edge case:** What if `extra_css_urls` in the metadata points at `/static/css/vendor/prism.css` (it does — see metadata.json line 70)? After Phase 4, this would route to the frontend, and since we're NOT copying vendor/prism.css into the frontend's static dir (phase 4 doesn't port `/how-to-use` which uses Prism), the frontend returns 404. That's fine because:
1. Phase 4 only serves `/` and `/{db}` — neither uses prism
2. Datasette's own HTML pages (like `/-/sql`) DO reference `/static/css/vendor/prism.css`, but those URLs (after the `.json`-or-not bifurcation) stay on datasette since they're under `/-/`
3. HOWEVER: datasette might try to reference `/static/css/vendor/prism.css` via `<link>` in pages like `/-/sql` — and the browser will fetch it via the Caddy path, which routes to frontend, 404. **Hazard.**

[ASSUMED — needs verification] If broken CSS on `/-/sql` matters (it's a dev surface per CONTEXT; probably doesn't), one fix is to copy prism.css into the frontend's static too. But per CONTEXT "`/-/sql` is developer surface, no frontend nav needed" — we likely don't care. Document the trade-off; don't fix in Phase 4.

## Production Deploy Mechanism

### Current state (verified)

- **No `docker-compose.prod.yml` exists.** Root directory has only `docker-compose.yml` with `auto_https off` in Caddyfile and no hostname site block.
- **Caddyfile has a prepared comment** (line 20-24): "Local dev / phase 3: plain HTTP only. Production overlay (docker-compose.prod.yml, future) will enable auto-HTTPS at the real hostname data.zeeker.sg by adding a hostname site block alongside this :80 block."
- **Production deploy recipe (from CONTEXT.md):** `git pull && docker compose up -d --build` on the production host.

### What Phase 4 must author (Plan 04-05)

1. **`Caddyfile.prod`** (or a second site block in `Caddyfile` gated by an ENV) — add a hostname site block for `data.zeeker.sg`:

```caddyfile
{
  # Production: no auto_https off — let Caddy provision TLS from Let's Encrypt
  admin localhost:2019
}

data.zeeker.sg {
  @datasette {
    path *.json *.csv *.db
    path /-/*
  }
  reverse_proxy @datasette zeeker-datasette:8001
  reverse_proxy frontend:8000
}

# Keep :80 for local-host testing (optional, can drop in prod)
:80 {
  redir https://data.zeeker.sg{uri} permanent
}
```

2. **`docker-compose.prod.yml`** — overlay that mounts `Caddyfile.prod` instead of dev `Caddyfile`, and adds any prod env vars (e.g., AWS creds that differ in prod):

```yaml
# docker-compose.prod.yml — overlay for production.
# Use: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
services:
  caddy:
    volumes:
      - ./Caddyfile.prod:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
```

3. **`scripts/verify_phase_04.sh`** — inherits `verify_phase_03.sh` pattern; adds positive + negative + CSS + font checks (see "Validation Architecture" section).

4. **Production smoke script** — either `verify_phase_04.sh` with `BASE_URL=https://data.zeeker.sg` env var (parameterize), or a separate `scripts/verify_production.sh` that hits the public hostname.

### Deploy sequence (from CONTEXT, refined)

```bash
# 1. On dev machine — prove local works
docker compose up -d --build
bash scripts/verify_phase_04.sh
# → all green before proceeding

# 2. Commit. Push.
git commit -am "feat: port home + database pages to frontend"
git push

# 3. On production host
ssh prod
cd /path/to/zeeker-datasette
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
sleep 30  # S3 download + healthchecks

# 4. Smoke check production
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh

# 5. If smoke fails: rollback
#    git log -1 --format=%H  # get commit hash
#    git revert HEAD
#    git push
#    (re-pull + up on prod, see step 3)
```

[ASSUMED] The production host's exact path and any SSH/deploy automation (if any) aren't documented in the repo. Phase 4 should document (in SUMMARY) the actual production process as used. If there's CI/CD, it's not visible in this repo.

## Runtime State Inventory

**Phase 4 is not a rename phase**, but it does deploy a new service path to production. Runtime state checklist:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — frontend is stateless. No SQLite, no user data, no session store. | None. |
| Live service config | Caddy stores TLS certs in `caddy_data` volume (persistent). Any production TLS cert earned during deploy is cached there — rollback won't revoke; good. | None. |
| OS-registered state | Docker container names (`zeeker-frontend`, `zeeker-datasette`, `zeeker-caddy`) already set in Phase 2. Systemd unit (if any) would reference `docker-compose.yml` by path, not by service name. | None — verify during production deploy that `docker compose ps` lists all 3 healthy. |
| Secrets/env vars | Datasette reads S3 creds from env; frontend has NO env secrets. `AWS_ACCESS_KEY_ID` etc. must NOT be in frontend's env (Phase-2 RESEARCH Pitfall 5). | **Verify** `environment:` block for `frontend` service in docker-compose.yml stays empty (just `PYTHONUNBUFFERED=1`). |
| Build artifacts / installed packages | Frontend Docker image rebuilds on `docker compose up --build`. Old image is untagged — if rollback needed immediately after deploy, `docker image ls` still has the prior-tagged one for 1 build cycle. | Document rollback image tag in SUMMARY (e.g., before deploy, `docker image tag zeeker-datasette-frontend:latest zeeker-datasette-frontend:pre-phase-04`). |

**The canonical question:** after every file in the repo is updated + `docker compose up --build`, what runtime systems still have the old behavior cached, stored, or registered?

Answer: only browser caches. Frontend's `Cache-Control: public, max-age=60` on `/` and `/{db}` means a user who loaded the site in the last minute gets the old HTML — acceptable. Browser font + CSS caches: without cache-busting, users might hold old CSS for up to ~7 days (typical font/CSS default cache). Fonts don't change. CSS changes during the port. **Mitigation: if post-deploy UI looks weird, a hard-refresh on the browser fixes it; we don't ship cache-busting in phase 4 per CONTEXT deferred.**

## Common Pitfalls

### Pitfall 1: Using `r.raise_for_status()` before handling 404

**What goes wrong:** `raise_for_status()` raises `HTTPStatusError` for any 4xx. If you call it before checking for 404, the handler crashes with a 500 instead of returning a proper 404 to the user.

**Why it happens:** Copy-pasted from happy-path examples.

**How to avoid:** Check `if r.status_code == 404: raise HTTPException(404)` FIRST, then `r.raise_for_status()` for genuine server errors.

**Warning signs:** `/unknown-db` returns 500 with stack trace instead of 404 HTML.

### Pitfall 2: Forgetting `"request": request` in TemplateResponse context

**What goes wrong:** `RuntimeError: request argument missing or not a valid Request type` (or similar Starlette error).

**Why it happens:** Copy-pasted from a Flask example (Flask doesn't require request passing).

**How to avoid:** Every `templates.TemplateResponse(...)` call MUST pass `{"request": request, ...}`. Starlette enforces it. [CITED: starlette.dev/templates]

**Warning signs:** 500 errors on every HTML route.

### Pitfall 3: Creating `httpx.AsyncClient()` inside the handler

**What goes wrong:** A new TCP connection per request. Added latency. No connection reuse.

**Why it happens:** Convenience. Looks fine in benchmarks that don't exercise load.

**How to avoid:** Lifespan pattern (see Pattern 1). Access `request.app.state.http` inside handlers.

**Warning signs:** `netstat -an | grep 8001` shows many short-lived connections under load; cache-miss latency is 2-5× higher than cache-hit.

### Pitfall 4: Iterating `metadata.databases` including the `*` wildcard key

**What goes wrong:** A spurious "database card" for `*` — probably renders a blank card with a broken link.

**Why it happens:** Datasette uses `*` as a wildcard metadata key for cross-cutting rules; it's not a real database.

**How to avoid:** Whenever iterating `metadata.databases.items()`, filter: `[k for k in dbs if k != "*"]`.

**Warning signs:** Home page has N+1 cards instead of N, with one card showing `*` or a broken URL.

### Pitfall 5: Filtering `_zeeker_*` with a string-prefix check instead of `hidden`

**What goes wrong:** FTS virtual tables (`headlines_fts`, `about_singapore_law_fts_data`, `*_fts_docsize`, etc.) appear in the editorial-row list. M1's `database.html` used to have this problem.

**Why it happens:** Reading the CLAUDE.md line "All `_zeeker_*` metadata tables are hidden from the UI" and taking it literally.

**How to avoid:** Use Datasette's `hidden: true` flag — it covers `_zeeker_*` AND FTS internals. [VERIFIED: curl /sglawwatch.json shows hidden=true on both categories.]

**Warning signs:** Database page shows a dozen `*_fts_*` rows.

### Pitfall 6: Base.html `extends` resolving to nothing (ambiguous with Datasette's `default:` prefix)

**What goes wrong:** Template compilation error like "base.html not found".

**Why it happens:** M1's templates use `{% extends "default:index.html" %}` — the `default:` prefix is a Datasette-specific directive. FastAPI's Jinja has no such concept; it only knows `Jinja2Templates(directory="...")`.

**How to avoid:** `base.html` lives in `templates/` alongside `index.html` and `database.html`. Use `{% extends "base.html" %}` — no prefix.

**Warning signs:** Jinja `TemplateNotFound` at first render.

### Pitfall 7: Jinja2 autoescape OFF

**What goes wrong:** XSS — a malicious table description in metadata.json could execute JS in a user's browser.

**Why it happens:** Hand-constructing `Environment(...)` instead of using `Jinja2Templates(directory=...)`.

**How to avoid:** Use `Jinja2Templates(directory=...)`. Starlette enables `select_autoescape(default_for_string=False)` for `.html`/`.htm`/`.xml` by default. [CITED: starlette.dev/templates]

**Verification:** Render a template with `{{ "<script>alert('x')</script>" }}` in the context; output should be escaped entities, not running JS.

**Warning signs:** A `<script>` in datasette metadata description actually executes.

### Pitfall 8: Dockerfile bloat from copying M1 artifacts into frontend package

**What goes wrong:** Frontend image jumps from 389MB to 500MB+ because someone copied all of M1's `static/` + `templates/` + `plugins/` into the package.

**Why it happens:** "Convenience" copy. The real need is just 3 woff2 files + 4 template files + 1 harvested CSS.

**How to avoid:** Harvest mechanically per the §CSS Harvest section. Only copy specific files listed in "Recommended Project Structure" above.

**Warning signs:** `docker images | grep frontend` shows > 450MB.

### Pitfall 9: Caddy's `max-age` on `/.json` masking stale data on the frontend

**What goes wrong:** Datasette sets `Cache-Control: public, max-age=300, s-maxage=3600` on `/.json`. If Caddy is configured as a caching proxy (it's not currently, but if ever changed), a rebuild of the datasette container wouldn't reflect for an hour.

**Why it happens:** Standard Cache-Control interaction.

**How to avoid:** Phase 4 doesn't change Caddy caching behavior. But: frontend's TTL cache should have a shorter TTL (60s suggested) than datasette's `s-maxage=3600`, so worst-case staleness is 60s + network propagation, not an hour.

**Warning signs:** A newly-deployed metadata change takes an hour to show up.

### Pitfall 10: `Cache-Control` on frontend HTML interacting with browser history navigation

**What goes wrong:** User goes to `/sglawwatch`, clicks to `/zeeker-judgements`, hits Back button — browser may serve the 60s-cached `/sglawwatch` HTML without revalidation, which is usually fine but confusing if the db count stat on the home page was wrong.

**Why it happens:** `max-age=60` directive does exactly that.

**How to avoid:** `stale-while-revalidate=300` (already in the CONTEXT-specified header) means the browser uses stale within 5min and refreshes in background — this is the usual accepted trade.

**Warning signs:** Rare. User confusion after stats change.

## Code Examples

All verified patterns from official/Context7 sources.

### Example 1: Lifespan + httpx pattern (Context7 FastAPI)

```python
# Source: fastapi.tiangolo.com/advanced/events via Context7 /websites/fastapi_tiangolo
from contextlib import asynccontextmanager
from fastapi import FastAPI
import httpx

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        timeout=httpx.Timeout(10.0, connect=2.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    yield
    await app.state.http.aclose()

app = FastAPI(title="zeeker-frontend", lifespan=lifespan)
```

### Example 2: Jinja2Templates with custom filters

```python
# Source: starlette.dev/templates + fastapi.tiangolo.com/reference/templating
from fastapi.templating import Jinja2Templates
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
# Autoescape is enabled by default by Starlette for .html/.htm/.xml templates.

# Register custom filters after construction.
templates.env.filters["filesizeformat"] = filters.filesizeformat
templates.env.filters["pluralize"] = filters.pluralize
templates.env.filters["safe_format"] = filters.safe_format
# Register helper functions as globals (so {{ s('key', 'default') }} works)
templates.env.globals["s"] = filters.s
templates.env.globals["plural"] = filters.plural
```

### Example 3: TemplateResponse with Cache-Control

```python
# Source: synthesized from fastapi.tiangolo.com/advanced/custom-response and starlette.dev/templates
from fastapi import Request
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    client = request.app.state.http
    r = await client.get("/.json")
    r.raise_for_status()
    databases = [{"name": k, **v} for k, v in r.json().items()]

    response = templates.TemplateResponse(
        request=request,  # FastAPI ≥ 0.112 lets you pass request as kwarg
        name="index.html",
        context={
            "databases": databases,
            "current_year": 2026,
            "metadata": {},  # fetched separately
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

### Example 4: Hidden-table filter (verified against live API)

```python
# Source: verified via curl http://localhost/sglawwatch.json 2026-04-22
# Datasette sets hidden=true on both _zeeker_* tables AND FTS internals.
# Single predicate covers both.
payload = (await client.get(f"/{db}.json")).json()
visible_tables = [t for t in payload.get("tables", []) if not t.get("hidden")]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Datasette's Jinja environment + `{% extends "default:..." %}` | FastAPI + Starlette's `Jinja2Templates` + `{% extends "base.html" %}` | Phase 4 (this phase) | Escapes Datasette's template override system — the entire rationale for this milestone (REQ-escape-datasette-template-surface, PRD §3) |
| `@app.on_event("startup")` / `@app.on_event("shutdown")` | `@asynccontextmanager` lifespan | FastAPI 0.93+ (2023) | Old events deprecated; lifespan is single source of truth. [CITED: fastapi.tiangolo.com/advanced/events] |
| Flask's `request.url_root` / Django's `url_for` for URL building | FastAPI lets you build URLs via `request.url_for(name, ...)` OR use literal strings | N/A — M1 already uses literal strings `/{{ database.name }}` | Zero change needed; literal string URLs survive the port |
| Datasette-server-rendered HTML for `/` and `/{db}` | FastAPI-rendered HTML via httpx JSON fetches | Phase 4 | User-visible: none (design locked). Architectural: monumental. |
| S3 overlay CSS + per-database templates (M1 era) | Single frontend-owned CSS + Jinja conditionals | Deferred to Phase 8 (per PRD §9) | Phase 4 does NOT drop the overlay mechanism; datasette's `extra_css_urls` still references `/static/css/vendor/prism.css` etc. Those URLs will 404 on phase-4 routes but that's fine — phase 4 doesn't render pages that use prism. |

**Deprecated/outdated:**
- `@app.on_event` startup/shutdown events — do not use
- Datasette's `default:` template prefix — not applicable in FastAPI
- Flask's `filesizeformat` filter — not portable as-is; must port the 15-line body from M1's `plugins/template_filters.py`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rolling a 20-line TTL cache class is cheaper than adding `cachetools` dep | Supporting / Pattern 2 | Low — swap to cachetools in 10 min if we regret it. |
| A2 | Stubbing `s()` and `plural()` (not porting strings.yaml) is acceptable | Jinja port map | Low — falls back to literal defaults, matches M1's rendered output 1:1. If i18n is ever wanted, re-add strings.yaml in Phase 6. |
| A3 | Cache-busting `?v=hash` on CSS/fonts is deferred; hard-refresh is acceptable | Pitfalls / CONTEXT deferred | Medium — first deploy might show old CSS briefly; documented. Real users will experience it; operator (user) accepts. |
| A4 | `/-/sql` still references `/static/css/vendor/prism.css` which will 404 after phase 4 | Static routing edge case | Low — `/-/sql` is a dev surface per CONTEXT; broken CSS there is acceptable. If it matters, copy prism into frontend static. |
| A5 | The tail `footer a:link` override in `zeeker.css` is no longer needed after the port (frontend doesn't load datasette's app.css) | CSS Harvest | Low — leaving it is harmless; removing is a minor cleanup. Suggest KEEPING it in the harvest for parity, revisit in Phase 8. |
| A6 | Production deploy is `git pull && docker compose up -d --build` on a single host (not CI/CD) | Production Deploy | Medium — if there's a CI/CD pipeline not visible in the repo, the deploy plan needs adjustment. **Ask user during planning.** |
| A7 | `docker-compose.prod.yml` and `Caddyfile.prod` don't exist and need to be authored in Phase 4 | Production Deploy | Low — verified in filesystem; authoring is a plan's worth of work (Plan 04-05). |
| A8 | Datasette's top-level `/{db}.json` `source`/`license` fields are merged from metadata.json at datasette-request time — so we don't need to also fetch `/-/metadata.json` just to show these in the database hero | Datasette JSON Contract | Low — VERIFIED via live curl. But: per-DB title/description ARE NOT in `/{db}.json` and DO require the metadata.json fetch. |
| A9 | The production host runs Docker Compose v2+ (supporting the `-f file1 -f file2` overlay pattern) | Production Deploy | Low — Phase 2/3 production is already using docker compose v2 per the healthcheck syntax. |

## Open Questions

1. **Does production have a CI/CD pipeline, or is it manual git-pull + compose up?**
   - What we know: CONTEXT.md says "`docker compose up -d --build` on the production host after git pull". No CI files (`.github/workflows/`, etc.) visible in the repo root.
   - What's unclear: if a deploy automation exists off-repo (GitOps agent, Watchtower, etc.), the deploy plan needs adjustment.
   - Recommendation: **Ask user at plan-time** (one-line question) or assume manual and document in Plan 04-05's verification notes.

2. **Should the frontend respect datasette's `extra_css_urls` / `extra_js_urls` from `/-/metadata.json`?**
   - What we know: M1's `index.html` and `database.html` don't reference these (metadata.json sets them but templates don't iterate them in the body — Datasette's `default:` base template did). After the port, we have a choice.
   - What's unclear: are there downstream users relying on per-DB custom CSS loaded via this mechanism?
   - Recommendation: **NO — drop it in Phase 4.** CONTEXT explicitly says per-DB overlays are a Phase-8 decision. Plan 04-05 can document the trade-off.

3. **Should Phase 4 re-baseline `phase-04-pre` BEFORE deploy or AFTER?**
   - What we know: CONTEXT.md says re-baseline "AFTER the deploy … wait until production is stable".
   - What's unclear: whether the Phase-3 baselines (`phase-03-pre`) remain valid through Phase 4. Answer: yes — Phase 4 adds frontend HTML routes only; `*.json` URLs still route to datasette unchanged. So `verify_api_parity.sh` with `ZEEKER_BASELINE_DIR=phase-03-pre` continues to pass.
   - Recommendation: Phase 4's verifier uses `phase-03-pre` (established baselines). Capture `phase-04-pre` post-deploy in Plan 04-05 as a Phase-5 preparation step.

4. **Is there a test framework scaffolded in `packages/zeeker-frontend/tests/`?**
   - What we know: `tests/` directory exists (Phase 2 scaffold). `pytest==9.0.3` is a dev dep. No test files authored.
   - What's unclear: whether Phase 4 should author minimal tests (Jinja render smoke, httpx mock unit tests) or defer.
   - Recommendation: **Author minimal tests — 1 per route** — `tests/test_home.py` and `tests/test_database.py` with an `httpx.MockTransport` that returns fixture JSON, asserts the template renders without error and key strings are present. Low cost, high value for refactor-confidence.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Frontend runtime | ✓ (in image) | 3.12.13 | — |
| uv | Image build | ✓ | From `ghcr.io/astral-sh/uv:latest` in Dockerfile | — |
| FastAPI | Route handlers | ✓ (via uv sync) | 0.136.0 | — |
| Jinja2 | Template rendering | ✓ | 3.1.6 | — |
| httpx | HTTP client | ✓ | 0.28.1 | — |
| Caddy | Reverse proxy + TLS (prod) | ✓ (container) | 2.11.2-alpine | — |
| Docker Compose | Local + prod orchestration | ✓ (implied by existing compose file) | v2+ | — |
| Docker | Build + run | ✓ | (running; verified) | — |
| M1 source tree (`templates/`, `static/css/zeeker-base.css`, `static/fonts/`) | Harvest source | ✓ | — | — |
| Live datasette service at `http://zeeker-datasette:8001` | Contract verification during build + smoke | ✓ (healthy, verified) | Datasette 0.65.2 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

**Dev-machine needs:** bash, curl, git, docker — all standard. `pytest` via `uv run pytest` inside the frontend package dir.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (already in `packages/zeeker-frontend/pyproject.toml` [dependency-groups].dev) |
| Config file | none — create `packages/zeeker-frontend/pyproject.toml [tool.pytest.ini_options]` section in Wave 0 OR use defaults |
| Quick run command | `cd packages/zeeker-frontend && uv run pytest tests/ -x` |
| Full suite command | `cd packages/zeeker-frontend && uv run pytest tests/ -v` |
| Smoke-check command (black-box) | `bash scripts/verify_phase_04.sh` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-frontend-route-set | `GET /` returns 200 with rendered home HTML | smoke | `curl -fsS http://localhost/ \| grep -q 'db-statband'` (in verify_phase_04.sh) | ❌ Wave 0 (verify_phase_04.sh) |
| REQ-frontend-route-set | `GET /{db}` returns 200 for existing DB | smoke | `curl -fsS http://localhost/sglawwatch \| grep -q 'db-header'` | ❌ Wave 0 |
| REQ-frontend-route-set | `GET /{unknown_db}` returns 404 | smoke | `curl -s -o /dev/null -w '%{http_code}' http://localhost/nonexistent-db \| grep -q '404'` | ❌ Wave 0 |
| REQ-frontend-route-set | `GET /` integrates data from `/.json` (db count matches) | integration | `pytest tests/test_home.py::test_shows_all_databases` (MockTransport fixture) | ❌ Wave 0 |
| REQ-frontend-route-set | `GET /{db}` filters hidden tables | integration | `pytest tests/test_database.py::test_filters_hidden_tables` | ❌ Wave 0 |
| REQ-frontend-route-set | Template renders without Jinja errors | unit | `pytest tests/test_templates.py::test_index_renders` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Home body does NOT contain `/static/css/zeeker-base.css` (M1 path) | smoke / negative | `curl -s http://localhost/ \| ! grep -q 'zeeker-base.css'` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Home body contains `/static/css/zeeker.css` (frontend path) | smoke / positive | `curl -s http://localhost/ \| grep -q '/static/css/zeeker.css'` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Database page body does NOT list `_zeeker_*` tables | smoke / negative | `curl -s http://localhost/sglawwatch \| ! grep -q '_zeeker'` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Database page body does NOT list `*_fts` tables | smoke / negative | `curl -s http://localhost/sglawwatch \| ! grep -q 'headlines_fts'` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Italic-accent H1 renders (Fraunces `<em>` inside H1) | smoke / visual | `curl -s http://localhost/ \| grep -qE '<h1>[^<]+<em>'` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Stat band element renders with expected class | smoke | `curl -s http://localhost/ \| grep -q 'db-statband'` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Card grid element renders | smoke | `curl -s http://localhost/ \| grep -q 'class="cards"'` | ❌ Wave 0 |
| REQ-eliminate-template-drift | Editorial-row list renders on database page | smoke | `curl -s http://localhost/sglawwatch \| grep -q 'class="list"' \|\| grep -q 'class="row"'` | ❌ Wave 0 |
| REQ-frontend-data-via-http | Frontend container has no sqlite client | build | `docker compose exec frontend sh -c 'command -v sqlite3'` should exit non-zero | ✓ (Phase-2 verifier covers this; delegate) |
| REQ-frontend-data-via-http | Frontend container has no data volume | build | `docker compose config \| grep -A5 'frontend:' \| ! grep -q '/data'` | ✓ (Phase-2 verifier) |
| REQ-api-byte-parity (inherited) | `verify_api_parity.sh` against `phase-03-pre` baselines | parity | `ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh` | ✓ (exists) |
| Static assets | `/static/css/zeeker.css` returns 200 with `text/css` MIME | smoke | `curl -sI http://localhost/static/css/zeeker.css \| grep -q 'text/css'` AND `grep -q '200 OK'` | ❌ Wave 0 |
| Static assets | `/static/fonts/inter-latin.woff2` returns 200 | smoke | `curl -sI http://localhost/static/fonts/inter-latin.woff2 \| grep -q '200 OK'` | ❌ Wave 0 |
| Static assets | `/static/fonts/jetbrains-mono-latin.woff2` returns 200 | smoke | same pattern | ❌ Wave 0 |
| Static assets | `/static/fonts/fraunces-latin.woff2` returns 200 | smoke | same pattern | ❌ Wave 0 |
| Phase-3 routing intact | `/sglawwatch.json` still routes to datasette | parity | `curl -s http://localhost/sglawwatch.json \| grep -q '"tables"'` | ✓ (via verify_phase_03.sh delegation) |
| Production smoke | `data.zeeker.sg/` returns 200 with expected shell | production | `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh` | ❌ Wave 0 (parameterize existing) |

### Sampling Rate

- **Per task commit:** `cd packages/zeeker-frontend && uv run pytest tests/ -x` — unit + integration tests, fast
- **Per wave merge:** `bash scripts/verify_phase_04.sh` — full black-box smoke against local stack
- **Phase gate:** Production smoke (`BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh`) green before marking phase complete

### Wave 0 Gaps

Phase 4 is net-NEW tests — no existing test infrastructure in `packages/zeeker-frontend/tests/`. Wave 0 must author:

- [ ] `packages/zeeker-frontend/tests/__init__.py`
- [ ] `packages/zeeker-frontend/tests/conftest.py` — shared `httpx.MockTransport` fixture + Datasette JSON fixtures (load from `tests/fixtures/*.json`)
- [ ] `packages/zeeker-frontend/tests/fixtures/databases.json` — captured from `curl http://localhost/.json`
- [ ] `packages/zeeker-frontend/tests/fixtures/sglawwatch.json` — captured from `curl http://localhost/sglawwatch.json`
- [ ] `packages/zeeker-frontend/tests/fixtures/metadata.json` — captured from `curl http://localhost/-/metadata.json`
- [ ] `packages/zeeker-frontend/tests/test_home.py` — covers home route (MockTransport-backed)
- [ ] `packages/zeeker-frontend/tests/test_database.py` — covers database route
- [ ] `packages/zeeker-frontend/tests/test_filters.py` — filesizeformat, pluralize, safe_format unit tests
- [ ] `scripts/verify_phase_04.sh` — black-box verifier (delegates to verify_phase_03.sh for inherited checks; adds Phase-4 positive/negative/static assertions)

Tests can run without the docker stack up — MockTransport gives the handler a fake datasette. `verify_phase_04.sh` requires the local stack running. Framework install is already complete (pytest in dev deps).

## Security Domain

Security enforcement defaults to ON (no `security_enforcement: false` in `.planning/config.json` — file isn't even present, so absent-is-enabled applies).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 4 has no auth surface — read-only HTML; site is public. |
| V3 Session Management | no | No sessions — stateless frontend. |
| V4 Access Control | no | All data is public (open civic data). Datasette `--cors` already set. |
| V5 Input Validation | yes | Pydantic path validation on `/{db}` (FastAPI does this automatically via type hint `db: str`; no injection surface since the string becomes a path in an httpx call — see V12). |
| V6 Cryptography | no | TLS is Caddy's job. Frontend never touches private keys or secrets. |
| V7 Error Handling | yes | Don't leak stack traces. FastAPI's default 500 response is JSON `{"detail": "Internal Server Error"}` — safe. 404 returns the raw datasette error dict? No — we raise `HTTPException(404)` explicitly. |
| V8 Data Protection | n/a | No user data. |
| V9 Communications | n/a | Internal HTTP between frontend and datasette on the Docker bridge; external TLS is Caddy. |
| V10 Malicious Code | yes | **Jinja2 autoescape** (Starlette default) prevents XSS from datasette metadata. |
| V11 Business Logic | no | Read-only pass-through. |
| V12 File and Resources | yes | Path traversal: `{db: str}` path parameter is used to construct `/{db}.json` — an attacker could try `/../.json` or `/%2E%2E%2F.json`. FastAPI's path validator rejects these (ASGI-layer). Datasette 404s on unknown db. |
| V13 API | yes | CORS already set at Datasette level; preserved (verified Phase 3). |
| V14 Configuration | yes | No secrets in frontend env (verified in Phase 2 setup). Container runs as non-root (inherited from python:3.12-slim default? [VERIFIED: no — uses root; known M2 deferral]). |

### Known Threat Patterns for FastAPI + Jinja2 + httpx stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via unescaped metadata | Tampering / Repudiation | Jinja2 autoescape enabled by default (Starlette's `Jinja2Templates`) — verified in Pattern 2 |
| SSRF via user-controllable httpx URL | Tampering | `httpx.AsyncClient(base_url=DATASETTE_URL)` + relative paths ONLY; no user input concatenated into URL (only `db` path param, sanitized by FastAPI's path validator to `^[^/]+$` effectively) |
| Path traversal via `{db}` | Tampering | FastAPI rejects `/` in path params by default (Starlette route matching); `..` collapses at the URL parser. Test: `curl http://localhost/..` returns 404 at frontend, not proxied as-is. |
| Jinja2 Server-Side Template Injection (SSTI) | Tampering / Elevation | All templates are developer-controlled; no user input reaches `jinja_env.from_string(...)` or similar. Context variables are pre-filtered before `TemplateResponse`. Safe. |
| Prototype pollution via JSON | Tampering | Python dicts aren't vulnerable like JavaScript; httpx.json() returns plain dicts. Safe. |
| Cache poisoning via Vary/Cache-Control | Tampering | `Cache-Control: public, max-age=60` is safe (no private content to leak). |
| Denial of service via slow datasette | Availability | `httpx.Timeout(10.0)` prevents hanging forever; FastAPI can serve other routes while the datasette call is in flight (async). |

All mitigations are standard library behavior — no custom code needed. The main enforcement is not disabling Jinja autoescape and not constructing URLs from user input.

## Sources

### Primary (HIGH confidence)

- **Context7 `/websites/fastapi_tiangolo`** — lifespan async context manager pattern, Jinja2Templates docs. [FETCHED 2026-04-22 via `npx ctx7@latest docs`]
- **`starlette.dev/templates`** — autoescape behavior in `Jinja2Templates(directory=...)` [CITED via WebSearch 2026-04-22]
- **`fastapi.tiangolo.com/advanced/events`** — lifespan is the recommended pattern superseding `on_event` [CITED via Context7]
- **`fastapi.tiangolo.com/reference/templating/`** — TemplateResponse reference [CITED via WebSearch]
- **Live curl against `http://localhost/.json`, `/sglawwatch.json`, `/-/metadata.json`, `/-/versions.json`** — ground-truth Datasette API response shapes [VERIFIED 2026-04-22; Datasette version 0.65.2]
- **`templates/index.html`, `templates/database.html`, `templates/_header.html`, `templates/_footer.html`** — M1 source for the port [READ fully 2026-04-22]
- **`static/css/zeeker-base.css`** — M1 CSS; banner-delimited sections mapped via grep [INSPECTED line ranges 2026-04-22]
- **`.planning/phases/01-editorial-shell-home-inventory/*-SUMMARY.md`** — M1 implementation notes; CSS section line numbers cross-referenced
- **`.planning/phases/04-port-home-database-pages/04-CONTEXT.md`** — locked decisions
- **`.planning/phases/04-port-home-database-pages/04-UI-SPEC.md`** — design contract pointer
- **`.claude/skills/sketch-findings-zeeker-datasette/SKILL.md`** — design contract summary

### Secondary (MEDIUM confidence)

- **WebSearch: "FastAPI lifespan asynccontextmanager httpx AsyncClient app.state connection pooling 2026"** — cross-verified with Context7 [MEDIUM — the Medium blog post pattern matches Context7 FastAPI docs]
- **WebSearch: "FastAPI Jinja2Templates autoescape XSS TemplateResponse 2026 best practice"** — cross-verified with Starlette docs
- **WebSearch: "Caddy auto-HTTPS docker-compose production overlay"** — general pattern confirmed, project-specific details need user confirmation

### Tertiary (LOW confidence)

- None flagged LOW that aren't already in the Assumptions Log.

## Metadata

**Confidence breakdown:**

- **Standard stack:** HIGH — all deps pinned in Phase-2 pyproject.toml; versions verified against PyPI; patterns verified against Context7/official docs
- **Datasette JSON contract:** HIGH — verified via live curl against the running prod-shape stack
- **Jinja binding port:** HIGH — all bindings enumerated via grep; M1 summaries confirm each
- **CSS harvest line ranges:** HIGH — banner-comment delimiters verified via grep; M1 summaries confirm section boundaries
- **FastAPI lifespan + httpx pattern:** HIGH — Context7 official docs
- **Production deploy mechanism:** MEDIUM — CONTEXT describes manual git-pull + compose; no CI/CD visible; A6 flagged for user confirmation
- **Cache-busting strategy:** MEDIUM — deferred per CONTEXT; A3 flagged
- **Tail `footer a:link` necessity post-port:** LOW — A5 flagged; verify during harvest plan

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — FastAPI, Jinja2, httpx, and Datasette 0.65 are all in stable/mature release lines; ecosystem unlikely to shift)

---

*Phase: 04-port-home-database-pages*
*Research produced for planner consumption: plans should be atomic per §Primary recommendation (5 plans).*

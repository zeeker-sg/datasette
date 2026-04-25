# Phase 5: Port table browse + row view — Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 17 (5 new Python modules, 2 main templates, 4 partials, 1 modified template, 1 modified Python module, 1 modified main.py, 1 modified CSS, 1 modified metadata.json, 4 new tests, 1 new verifier)
**Analogs found:** 16 / 17 (only `urls.py` has no in-repo analog — port from `.venv/datasette/utils/__init__.py`; treat the dependency surface as the analog)

All analogs come from the **Phase 4 outputs** under `packages/zeeker-frontend/` plus the existing M1 reference templates under `templates/`. The Phase 4 chain is intentionally the closest mirror by design (CONTEXT §carry-forwards explicitly enumerates the patterns to inherit).

---

## File Classification

| Target File | Status | Role | Data Flow | Closest Analog | Match |
|-------------|--------|------|-----------|----------------|-------|
| `packages/zeeker-frontend/src/zeeker_frontend/routes_table.py` | NEW | route-handler | request-response (read-through HTTP) | `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py` | exact (same APIRouter / app.state.http / TemplateResponse / Cache-Control shape) |
| `packages/zeeker-frontend/src/zeeker_frontend/routes_row.py` | NEW | route-handler | request-response (read-through HTTP) | `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py` | exact (same shape; row.html instead of database.html, fetch_row instead of fetch_database) |
| `packages/zeeker-frontend/src/zeeker_frontend/urls.py` | NEW | utility module (pure functions) | transform | `.venv/lib/python3.12/site-packages/datasette/utils/__init__.py:268-331, 1173-1186` (port target — read-only reference) + `packages/zeeker-frontend/src/zeeker_frontend/filters.py` (in-repo style/structure analog) | role-match (no in-repo querystring helper exists; filters.py shows the file-shape convention) |
| `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` | MODIFIED | service / HTTP client | request-response | `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` (existing `fetch_database` is the within-file analog) | exact (extend same module; new fns mirror `fetch_database` shape) |
| `packages/zeeker-frontend/src/zeeker_frontend/main.py` | MODIFIED | app config / router registration | startup wiring | `packages/zeeker-frontend/src/zeeker_frontend/main.py:84-102` (existing `home_router` + `database_router` registration) | exact (append two `include_router` calls in same style) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/table.html` | NEW | template (Jinja) | render | `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` | exact (extends base.html, db-header + statband + toolbar shell carry-forward; mode dispatch is the new addition) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/row.html` | NEW | template (Jinja) | render | `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` | role-match (same extends pattern; row content body is novel — driven by row_mode) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/feed_card.html` | NEW (optional) | template partial | render | `templates/_table-sg-gov-newsrooms-mlaw_news.html` (M1 reference; reads slot conventions only — DO NOT copy verbatim) | role-match (slot pattern only) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/facet_sidebar.html` | NEW | template partial | render | none in-repo (new component) | NO ANALOG (author from UI-SPEC + sketch `references/directory-and-feed-lists.md`) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/pagination.html` | NEW | template partial | render | none in-repo (new component) | NO ANALOG (author from UI-SPEC §Pagination) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/applied_facets.html` | NEW | template partial | render | none in-repo (new component) | NO ANALOG (author from UI-SPEC §Applied-facet chips) |
| `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` | MODIFIED | stylesheet (append section) | n/a | self — existing `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` section at line 938 is the structural analog | exact (same delimiter convention; insert before footer-override block at line 1082) |
| `metadata.json` | MODIFIED | config (display hints) | n/a | `metadata.json` (self — existing `databases.sg-gov-newsrooms.tables.mlaw_news` entry is the structural analog) | exact (extend the existing per-table objects with `display.*` blocks) |
| `packages/zeeker-frontend/tests/test_routes_table.py` | NEW | test (integration) | request-response | `packages/zeeker-frontend/tests/test_database.py` | exact (same MockTransport + ASGITransport pattern; same fixture/clear-cache fixture; same assertion style) |
| `packages/zeeker-frontend/tests/test_routes_row.py` | NEW | test (integration) | request-response | `packages/zeeker-frontend/tests/test_database.py` | exact |
| `packages/zeeker-frontend/tests/test_urls.py` | NEW | test (unit) | transform | `packages/zeeker-frontend/tests/test_filters.py` | exact (same pure-function class-grouped pytest style) |
| `packages/zeeker-frontend/tests/test_datasette_client_table_row.py` | NEW (or extend existing test_database) | test (unit) | request-response | `packages/zeeker-frontend/tests/test_database.py` mock-handler block + (no separate datasette_client unit test exists yet) | role-match (use MockTransport handler pattern from test_database) |
| `scripts/verify_phase_05.sh` | NEW | verifier-script (bash) | sequential structural assertions over HTTP | `scripts/verify_phase_04.sh` | exact (delegate to phase_04 first, then mirror sections B–G shape) |

---

## Pattern Assignments

### `routes_table.py` (route-handler, request-response) — NEW

**Analog:** `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py`

**Imports + module shape pattern** (`routes_database.py:1-12`):
```python
"""GET /{db} — database overview page. Phase 4."""
from __future__ import annotations

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from zeeker_frontend.datasette_client import fetch_database, fetch_site_metadata

router = APIRouter()
```

**Core handler pattern — full skeleton to mirror** (`routes_database.py:15-72`):
```python
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

    # ... metadata merge ...
    site_metadata = await fetch_site_metadata(client)
    db_entry = (site_metadata.get("databases") or {}).get(db) or {}

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="database.html",
        context={...},
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

**Differences the planner must call out** (vs analog):
1. **Path signature changes** — decorator becomes `@router.get("/{db}/{table}", response_class=HTMLResponse)` and signature is `async def table_page(request: Request, db: str, table: str):`.
2. **Hidden-table guard at route entry** (Pitfall 6 in RESEARCH) — analog filters tables in a list-comprehension; **here it must guard at route boundary** before any fetch:
   ```python
   _HIDDEN_TABLE_PREFIXES = ("_zeeker",)
   _HIDDEN_TABLE_SUFFIXES = ("_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config")
   if table.startswith(_HIDDEN_TABLE_PREFIXES) or table.endswith(_HIDDEN_TABLE_SUFFIXES):
       raise HTTPException(status_code=404, detail="Table not found")
   ```
3. **Querystring forwarding** — analog ignores `request.query_params`; new handler forwards to `fetch_table(client, db, table, dict(request.query_params))` and `fetch_table` is responsible for the allowlist (Pitfall 7).
4. **`next_url` rewrite** (Pitfall 2) — `fetch_table` payload's `next_url` is a fully-qualified URL pointing to `.json` on the internal docker hostname. Handler must `urlparse(...)` and rebuild as `f"/{db}/{table}?{parsed.query}"`. **Analog has no equivalent** — `fetch_database` returns no pagination state.
5. **Per-table metadata access path** is one level deeper than analog: `(site_metadata.get("databases") or {}).get(db, {}).get("tables", {}).get(table, {})` (vs analog's `.get(db, {})`).
6. **Display dispatch context keys** — handler must add `table_mode`, `display`, `request_qs`, `facet_results`, `primary_keys`, `columns`, `rows`, `next_url` to context (none of which appear in analog).

**Anchor lines/conventions to preserve verbatim:**
- `client: httpx.AsyncClient = request.app.state.http` — lifespan-scoped client, no module-level httpx import or local AsyncClient construction.
- `try: ... except httpx.HTTPError: raise HTTPException(status_code=503, ...)` — 503 not 500.
- `if payload is None: raise HTTPException(status_code=404, ...)` — explicit 404 BEFORE other rendering.
- `response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"` — exactly this string (verifier greps for it).
- `request.app.state.templates.TemplateResponse(request=request, name=..., context={...})` — keyword form with `request=` first; do NOT import templates directly (avoids the circular-import trap noted in `main.py:80-82`).
- `from datetime import datetime` + `"current_year": datetime.now().year` in context (base.html footer needs it).

---

### `routes_row.py` (route-handler, request-response) — NEW

**Analog:** `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py`

Mirror everything from `routes_table.py` above, with these differences:

1. **Decorator + signature**: `@router.get("/{db}/{table}/{pk}", response_class=HTMLResponse)` / `async def row_page(request: Request, db: str, table: str, pk: str):`.
2. **Use `fetch_row(client, db, table, pk)`** instead of `fetch_table`. No querystring allowlist needed for the row endpoint (datasette ignores most params on `/row.json`).
3. **No `next_url` rewrite** — single-row endpoint has no pagination.
4. **`row_mode` dispatch** — pull `display.row_mode` (default `"tabular"`).
5. **Same hidden-table prefix/suffix guard** at the route boundary (`if table.startswith(...) or table.endswith(...)`).
6. **404 copy** changes per UI-SPEC: `"Record not found. No row with primary key '{pk}' in '{table}'."`.
7. **Breadcrumbs grow one level**: `[{"href": f"/{db}", "label": db_title}, {"href": f"/{db}/{table}", "label": table_title}, {"label": pk_truncated_to_12_chars}]`.

---

### `urls.py` (utility module, transform) — NEW

**Primary analog (port target — READ-ONLY external reference):** `.venv/lib/python3.12/site-packages/datasette/utils/__init__.py:268-331, 1173-1186`

**In-repo style analog:** `packages/zeeker-frontend/src/zeeker_frontend/filters.py` (shows the file-header / docstring / `from __future__ import annotations` convention)

**Core helper signatures to implement** (per RESEARCH §Querystring Helpers):
```python
"""Querystring helpers + tilde-encoded row URL builder.

Direct ports of datasette/utils/__init__.py:268-331 (path_with_*_args) and
:1173-1186 (tilde_encode). Pure functions; no I/O.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode

def path_with_added_args(path: str, query_string: str, args) -> str: ...
def path_with_replaced_args(path: str, query_string: str, args) -> str: ...
def path_with_removed_args(path: str, query_string: str, keys: set[str]) -> str: ...
def toggle_facet_value(path: str, qs: str, col: str, val: str) -> str: ...
def clear_facet_value(path: str, qs: str, col: str, val: str) -> str: ...
def set_sort(path: str, qs: str, col: str, current_state: str | None) -> str: ...
def export_url(db: str, table: str, ext: str, query_string: str) -> str: ...
def tilde_encode(s: str) -> str: ...
def row_url(db: str, table: str, pk_values: list[str]) -> str: ...
```

**Concrete implementation excerpts to copy** (verbatim from RESEARCH §Pattern 2):
```python
def path_with_added_args(path: str, query_string: str, args) -> str:
    if isinstance(args, dict):
        args = list(args.items())
    args_to_remove = {k for k, v in args if v is None}
    current = [(k, v) for k, v in parse_qsl(query_string) if k not in args_to_remove]
    current.extend([(k, v) for k, v in args if v is not None])
    qs = urlencode(current)
    return f"{path}?{qs}" if qs else path

def tilde_encode(s: str) -> str:
    SAFE = set(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._")
    out = []
    for byte in s.encode("utf-8"):
        if byte in SAFE:
            out.append(chr(byte))
        else:
            out.append(f"~{byte:02X}")
    return "".join(out)

def row_url(db: str, table: str, pk_values: list[str]) -> str:
    encoded = ",".join(tilde_encode(str(v)) for v in pk_values)
    return f"/{db}/{table}/{encoded}"
```

**Anchor convention:** Register all helpers as **Jinja globals** in `main.py` so templates call `{{ path_with_added_args(...) }}` directly — mirrors how `s` and `plural` are exposed today (`main.py:77-78`):
```python
templates.env.globals["path_with_added_args"] = urls.path_with_added_args
templates.env.globals["path_with_replaced_args"] = urls.path_with_replaced_args
templates.env.globals["path_with_removed_args"] = urls.path_with_removed_args
templates.env.globals["set_sort"] = urls.set_sort
templates.env.globals["export_url"] = urls.export_url
templates.env.globals["row_url"] = urls.row_url
```

**Difference vs port target:** The datasette source uses `MultiDict`/`MultiParams` for the query-string container; the port uses `parse_qsl`/`urlencode` from stdlib (no extra deps). RESEARCH already validated this substitution is correct for the helpers' contract.

---

### `datasette_client.py` (service, request-response) — MODIFIED

**Analog:** within-file — the existing `fetch_database` function (`datasette_client.py:30-40`).

**Existing pattern to extend** (`datasette_client.py:30-40`):
```python
async def fetch_database(client: httpx.AsyncClient, db: str) -> dict | None:
    """GET /{db}.json → payload dict, or None on 404.

    Per RESEARCH Pitfall 1: check 404 BEFORE raise_for_status() so callers
    can distinguish "database missing" from "upstream server error".
    """
    r = await client.get(f"/{db}.json")
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
```

**New `fetch_table` to add** (RESEARCH lines 716-741):
```python
async def fetch_table(
    client: httpx.AsyncClient,
    db: str,
    table: str,
    params: dict | None = None,
) -> dict | None:
    """GET /{db}/{table}.json with allowlisted params; None on 404, raises on other errors."""
    ALLOWED = {
        "_size", "_sort", "_sort_desc", "_search", "_next",
        "_facet", "_facet_array", "_facet_date",
    }
    safe_params = {"_shape": "objects"}  # Pitfall 1 — always object-shape rows
    for k, v in (params or {}).items():
        if k in ALLOWED or "__" in k:  # column__exact / column__contains etc.
            safe_params[k] = v
        elif not k.startswith("_"):     # plain column-name filters
            safe_params[k] = v
    r = await client.get(f"/{db}/{table}.json", params=safe_params)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
```

**New `fetch_row` to add:**
```python
async def fetch_row(client: httpx.AsyncClient, db: str, table: str, pk: str) -> dict | None:
    """GET /{db}/{table}/{pk}.json — single row; None on 404."""
    r = await client.get(f"/{db}/{table}/{pk}.json", params={"_shape": "objects"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
```

**Differences vs analog (`fetch_database`):**
1. **Always pass `_shape=objects`** — analog has no `params` arg. This eliminates the `list[list]` row trap (Pitfall 1).
2. **Querystring allowlist on `fetch_table`** — analog forwards no params; `fetch_table` filters known datasette params + `column__operator` patterns + plain column names; everything else dropped (Pitfall 7 / SSRF surface).
3. **No metadata-cache integration needed** — these endpoints are not cacheable in-process (per-request data); only `fetch_site_metadata` keeps the 60s TTL cache.

**Anchor conventions to preserve:**
- 404 check before `raise_for_status()` (the established pitfall-1 pattern).
- Return `dict | None`, raise on other HTTP errors (caller catches `httpx.HTTPError` and converts to 503).
- Type-hint the client parameter as `httpx.AsyncClient`.

---

### `main.py` (router registration) — MODIFIED

**Analog:** within-file — existing router registration block (`main.py:84-102`).

**Existing block to mirror** (`main.py:84-102`):
```python
from zeeker_frontend.routes_home import router as home_router
from zeeker_frontend.routes_database import router as database_router


# Explicit JSON healthcheck MUST register before the `/{db}` catch-all in
# database_router; otherwise `/frontend-test` matches the database route and
# the docker healthcheck + verify_phase_0{2,3}.sh reachability probes break.
@app.get("/frontend-test")
def frontend_test() -> dict[str, str]:
    return {"status": "ok", "service": "zeeker-frontend"}


app.include_router(home_router)
app.include_router(database_router)
```

**Append for Phase 5:**
```python
from zeeker_frontend.routes_table import router as table_router
from zeeker_frontend.routes_row import router as row_router

app.include_router(table_router)
app.include_router(row_router)
```

**Plus** Jinja-global registrations for the new `urls.py` helpers (mirror the `s` / `plural` lines at `main.py:77-78`):
```python
from zeeker_frontend import urls as zurls
templates.env.globals["path_with_added_args"] = zurls.path_with_added_args
templates.env.globals["path_with_replaced_args"] = zurls.path_with_replaced_args
templates.env.globals["path_with_removed_args"] = zurls.path_with_removed_args
templates.env.globals["set_sort"] = zurls.set_sort
templates.env.globals["export_url"] = zurls.export_url
templates.env.globals["row_url"] = zurls.row_url
```

**CRITICAL — registration order** (CONTEXT §Integration Points): FastAPI matches routes in declaration order, but **static paths win over parameterized**, so:
- `/frontend-test` → `home_router` (`/`) → `database_router` (`/{db}`) → `table_router` (`/{db}/{table}`) → `row_router` (`/{db}/{table}/{pk}`).
- The `/frontend-test` literal MUST stay before `database_router` — already enforced by the comment at `main.py:88-90`. The same comment principle applies if any future literal path needs to share the `/{db}` namespace.

**Anchor convention:** Imports go in the existing inline-import block right before the `app.include_router` calls — this is intentional in the analog (avoids module-level cycle; routers must be importable AFTER `app.state.templates` is set on line 82).

---

### `templates/table.html` (template, render) — NEW

**Analog:** `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html`

**Shell pattern to mirror** (`database.html:1-63`):
```jinja
{% extends "base.html" %}

{% block head %}
{% if metadata and metadata.description %}
<meta name="description" content="{{ metadata.description }}">
{% elif metadata and metadata.title %}
<meta name="description" content="Explore the {{ metadata.title }} database">
{% endif %}
{% endblock %}

{% block content %}
{# --- Editorial hero ------------------------------------------- #}
<header class="db-header">
  <div class="container">
    <div class="db-header-grid">
      <div>
        <div class="kicker">№ 01 · Database</div>
        <h1>
          {% set db_title = metadata.title if metadata and metadata.title else (database|replace('-', ' ')|replace('_', ' ')|title) %}
          {# Italicize only the trailing word (M1 WARN-04 logic) #}
          {% if ' ' in db_title %}
            {% set idx = db_title.rfind(' ') %}
            {{ db_title[:idx] }} <em>{{ db_title[idx+1:] }}</em>
          {% else %}
            <em>{{ db_title }}</em>
          {% endif %}
        </h1>
        ...
      </div>
      <dl class="meta-col">
        ...
      </dl>
    </div>
  </div>
</header>
```

**Stat-band pattern to mirror** (`database.html:66-97`) — same `<div class="db-statband">` shell; replace per-table-list aggregations with table-page numbers (filtered_table_rows_count, columns count, page size when filtered).

**Mode-dispatch addition** (no analog — author per RESEARCH §Pattern 3):
```jinja
{# --- Layout dispatch on display.table_mode --- #}
{% if table_mode == "feed" %}
  {% include "_partials/table_feed.html" %}
{% elif table_mode == "longform-list" %}
  {% include "_partials/table_longform_list.html" %}
{% else %}
  {# default: tabular fallback (D-04) #}
  {% include "_partials/table_tabular.html" %}
{% endif %}
```

**Differences vs analog:**
1. **Kicker text changes**: `"№ 01 · Database"` → `"№ 01 · {{ table_meta.title or table }}"` per UI-SPEC.
2. **No "by-table-list" loop** — analog renders `{% for table in vt %}`; new template renders `{% for row in rows %}` inside whatever mode-partial is included.
3. **Sticky toolbar must include FTS form + applied-facet chips + sort indicator + export anchors** (UI-SPEC §Toolbar contents). Analog's toolbar has only a search-tables filter form.
4. **Export anchors are direct suffix routes** (D-05): `<a href="/{{ database }}/{{ table }}.csv?{{ request_qs }}">CSV ↗</a>` — not the database-level `.csv`/`.db`/`.json` triple from analog (database export had no per-row context).
5. **No views/canned-queries sections** — those belong to `database.html`.
6. **`feed-layout` two-column grid** with `.facets` sidebar wraps the dispatch when facets are present (per UI-SPEC).

**Anchor conventions to preserve verbatim from analog:**
- `{% extends "base.html" %}` (NOT `{% extends "default:table.html" %}` — the M1 datasette-prefixed extends is forbidden; see M1 reference `templates/table.html:1` which we must NOT copy).
- `{% block content %}` is the only block populated; nav + breadcrumb + footer come from `base.html`.
- Italic-accent H1 split using `db_title.rfind(' ')` — verifier greps for `<h1>...<em>...</em>...</h1>` (`verify_phase_04.sh:62`); skipping the split breaks the assertion.
- `{% set table_meta = (metadata.tables[table.name] if metadata and metadata.tables and table.name in metadata.tables else {}) %}` — defensive lookup pattern (avoids `KeyError` under Starlette's strict Jinja); use the same idiom for `display = table_meta.get('display') or {}` access in the template (or pre-compute in handler).

---

### `templates/row.html` (template, render) — NEW

**Analog:** `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` (shell only).

Mirror the `{% extends "base.html" %}` + `{% block content %}` + `db-header` + breadcrumb-via-context shell. Then dispatch on `row_mode`:

```jinja
{% if row_mode == "article" %}
  {% include "_partials/row_article.html" %}
{% elif row_mode == "judgment" %}
  {% include "_partials/row_judgment.html" %}
{% elif row_mode == "longform" %}
  {% include "_partials/row_longform.html" %}
{% else %}
  {# default: tabular key-value <dl> #}
  {% include "_partials/row_tabular.html" %}
{% endif %}
```

**Differences vs analog:**
- **No stat band** — UI-SPEC §Always-present chrome explicitly excludes it ("row page competes with article").
- **H1 source** is the row's title-slot value (`row[display.columns.title]`) when `row_mode == "article"`; for `tabular` fallback, H1 is `"Record"` (UI-SPEC §Copywriting).
- **Long-text expand** (UI-SPEC §Interaction Contracts): in `row_tabular.html`, fields with `value|length > 200` get `<details><summary>Show full content</summary>{{ value }}</details>`.

---

### `templates/_partials/feed_card.html` (partial, render) — NEW (optional consolidation)

**Reference (do NOT copy verbatim):** `templates/_table-sg-gov-newsrooms-mlaw_news.html` (M1 partial — slot mapping reference only).

**M1 slot-mapping pattern** (`_table-sg-gov-newsrooms-mlaw_news.html:7-30`):
```jinja
{% for row in display_rows %}
    {% set card_row = row %}
    {% set card_title_col = "title" %}
    {% set card_date_col = "published_date" %}
    {% set card_pill_col = "category" %}
    {# BLK-04: use namespace so cls survives the if/elif scope. #}
    {% set _cat = (row["category"] or '')|lower %}
    {% set ns = namespace(cls='press-release') %}
    {% if 'speech' in _cat %}{% set ns.cls = 'speech' %}
    {% elif 'announcement' in _cat %}{% set ns.cls = 'announcement' %}
    {% elif 'newsletter' in _cat %}{% set ns.cls = 'newsletter' %}
    {% endif %}
    {% set card_pill_class = ns.cls %}
    {% set card_body_col = "content" %}
    {% set card_source_url_col = "source_url" %}
    {% set card_id_col = "id" %}
    {% set card_row_href = urls.row(database, table, row[primary_keys[0]]) if primary_keys else '' %}
    {% include "_partials/feed_card.html" %}
{% endfor %}
```

**Key insight to extract:** the M1 partials encode **column-slot decisions** (`card_title_col = "title"`, `card_date_col = "published_date"`, `card_pill_col = "category"`). In Phase 5 these become **`display.columns` keys in metadata.json** — read once in handler or template, NOT one partial per table. The hardcoded category-class branching (`speech` / `announcement` / `newsletter` / `press-release`) ports to Phase 5 either as CSS class derivation in the partial or as static category-pill class names mapped from the kicker value.

**`urls.row(...)` (M1's helper) ports to `row_url(database, table, [row[pk_col]])` from `urls.py`.** Note the M1 call passes a scalar; the new helper takes a list — wrap single-PK values: `row_url(database, table, [row[primary_keys[0]]]) if primary_keys else ('/' ~ database ~ '/' ~ table ~ '/' ~ row.rowid)` (Pitfall 4 fallback).

**Differences:** the new partial reads slot column names from `display.columns.{kicker,title,byline,body,date,source_url}` (handler-passed dict), not from per-template `{% set %}` blocks. One partial; data-driven.

---

### `static/css/zeeker.css` (stylesheet, append) — MODIFIED

**Analog:** within-file — existing `/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */` section starting at **line 938**.

**Existing section delimiter convention** (`zeeker.css:938`):
```css
/* =========== DATABASE EDITORIAL ROWS — phase 01 ============ */

.list {
  border-top: 2px solid var(--color-ink);
}
.list .row {
  display: grid;
  grid-template-columns: 60px 1fr 280px 130px 130px;
  gap: var(--space-6);
  align-items: baseline;
  padding: var(--space-6) var(--space-8);
  ...
```

**Footer-override block to preserve at TAIL** (`zeeker.css:1080-1099` — verifier-load-bearing, do NOT push past it):
```css
/* ----------------------------------------------------------------
 * FOOTER LINK OVERRIDE — must remain at TAIL of file to win cascade
 * against Datasette's /-/static/app.css `footer a:link` rule.
 * See .planning/notes/datasette-styling-limits.md WARN-05.
 * ---------------------------------------------------------------- */
footer a:link, footer a:visited, footer a:active { ... }
```

**Insertion point:** insert the new section IMMEDIATELY BEFORE the `HARVESTED FROM M1 zeeker-base.css LINES 4097..4116` comment block at line 1077 (which precedes the FOOTER LINK OVERRIDE). Use this delimiter (per RESEARCH §Section delimiter convention):

```css
/* =========== TABLE BROWSE + ROW VIEW — phase 05 ============ */

/* feed-layout grid + facets sidebar + ... */
```

**Section content sources:**
- **Direct copy from M1** (`static/css/zeeker-base.css:3864-3984` — feed-card classes `.va-feed`, `.va-empty`, `.va-item-wrap`, `.va-citation`, `.va-item`, `.va-item-head`, `.va-item-title`, `.va-item-excerpt`, `.va-item-foot`, `.source-host`).
- **Author from sketch references** for the rest — see RESEARCH §M1 CSS Harvest Plan rows where `Action = (new)` for the line-count budget. Do NOT search M1 for `.feed-layout` / `.facets` / `.article` / `.aside` / `.dateline` / `.coda` / `.data-table` / `.filter-chip` / `.pagination` — RESEARCH already verified those classes don't exist there (verification command at lines 532-534).

**Anchor convention:** every CSS variable referenced (`--color-*`, `--space-*`, `--text-*`, `--font-*`, `--tracking-*`, `--leading-*`, `--shadow-*`) must already be defined in `:root` (see `zeeker.css:85-135` for the existing token table). Do NOT introduce new tokens; the design-system lock means every value is pre-defined.

---

### `metadata.json` (config, declarative) — MODIFIED

**Analog:** within-file — existing `databases.sg-gov-newsrooms.tables.mlaw_news` block (`metadata.json:19-32`).

**Existing per-table object shape** (`metadata.json:19-32`):
```json
"mlaw_news": {
  "title": "Ministry of Law News",
  "description": "Press releases, speeches, parliamentary speeches, and announcements from the Ministry of Law Singapore (2026 onwards). Full article text is stored but not displayed; use the AI-generated summary for search and reading.",
  "columns": {
    "id": "Unique identifier (SHA-256 hash of source URL)",
    "title": "Title of the news item or speech",
    ...
  }
}
```

**Phase 5 extension — add a `display` key alongside the existing `title`/`description`/`columns`:**
```json
"mlaw_news": {
  "title": "Ministry of Law News",
  "description": "...",
  "columns": { ... existing ... },
  "display": {
    "table_mode": "feed",
    "row_mode": "article",
    "columns": {
      "kicker": "category",
      "title": "title",
      "byline": "published_date",
      "body": "summary",
      "date": "published_date",
      "source_url": "source_url"
    }
  }
}
```

**Tables to add `display.*` blocks to** (per RESEARCH §Display-Hint Schema Confirmation):

| DB | Table | Hint |
|----|-------|------|
| `sglawwatch` | `headlines` | `feed` / `article`, slots: kicker=category, title=title, byline=author, body=summary, date=date, source_url=source_link |
| `sglawwatch` | `about_singapore_law` | `longform-list` / `longform`, slots: kicker=section, title=title, date=last_scraped, source_url=item_url |
| `Zeeker-Judgements` | `judgments` | `tabular` / `judgment`, slots: title=case_name, kicker=court, citation=citation, date=decision_date, body=text, source_url=source_url |
| `sg-gov-newsrooms` | `mlaw_news`, `judiciary_news`, `acra_news`, `agc_news`, `ccs_news`, `ipos_news`, `mom_news`, `pdpc_news` (8 tables) | `feed` / `article` (same slot mapping as mlaw_news above; vary `kicker` to `content_type` for `judiciary_news`) |

**Differences vs analog:** the existing per-table objects have `title`/`description`/`columns`; the new `display` object nests **alongside** these (no replacement, no deletion of existing keys).

**Anchor conventions:**
- Only edit per-database `tables` objects under `databases.{db_name}.tables.{table_name}`. Do NOT add `display.*` to `databases.*` (the wildcard) — RESEARCH verified the wildcard's `tables` does not propagate the merge for hint lookups.
- `databases.*.tables._zeeker_schemas.hidden = true` (existing) stays untouched.
- The two-space JSON indentation already in the file is the project convention; preserve it.

---

### `tests/test_routes_table.py` (test, integration) — NEW

**Analog:** `packages/zeeker-frontend/tests/test_database.py`

**Mock-handler skeleton** (`test_database.py:18-34`):
```python
def _mock_datasette(sglawwatch_fixture, metadata_fixture):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/sglawwatch.json":
            return httpx.Response(200, json=sglawwatch_fixture)
        if path == "/-/metadata.json":
            return httpx.Response(200, json=metadata_fixture)
        return httpx.Response(
            404,
            json={"ok": False, "error": "Database not found", "status": 404, "title": None},
        )
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )
```

**Test-client fixture** (`test_database.py:37-47`):
```python
@pytest.fixture
async def client_with_mocked_datasette(sglawwatch_fixture, metadata_fixture):
    app.state.http = _mock_datasette(sglawwatch_fixture, metadata_fixture)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()
```

**Cache-clearing autouse fixture** (`test_database.py:11-15`):
```python
@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()
```

**Assertion patterns to mirror** (`test_database.py:51-120`):
```python
@pytest.mark.asyncio
async def test_database_returns_200_with_editorial_list(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/sglawwatch")
    assert r.status_code == 200
    body = r.text
    assert "db-header" in body
    assert "/static/css/zeeker.css" in body
    assert "zeeker-base.css" not in body

@pytest.mark.asyncio
async def test_database_cache_control_header(client_with_mocked_datasette):
    r = await client_with_mocked_datasette.get("/sglawwatch")
    cc = r.headers.get("cache-control", "")
    assert "max-age=60" in cc
    assert "stale-while-revalidate=300" in cc

@pytest.mark.asyncio
async def test_database_italic_accent_h1(client_with_mocked_datasette):
    import re
    r = await client_with_mocked_datasette.get("/sglawwatch")
    pattern = re.compile(r"<h1>.*?<em>[^<]+</em>.*?</h1>", re.DOTALL)
    assert pattern.search(r.text), "italic-accent H1 not found"
```

**Differences vs analog:**
1. **New mock paths needed**: `/sglawwatch/headlines.json` (with `_shape=objects` query) → returns `headlines_table` fixture; `/sglawwatch/about_singapore_law.json` → returns `about_singapore_law_table` fixture (for rowid-PK test). Add to handler:
   ```python
   if path == "/sglawwatch/headlines.json":
       return httpx.Response(200, json=headlines_table_fixture)
   ```
2. **New fixtures required** (RESEARCH §Wave 0 Gaps):
   - `tests/fixtures/headlines_table.json` — captured `/sglawwatch/headlines.json?_shape=objects&_size=10&_facet=category` payload
   - `tests/fixtures/about_singapore_law_table.json` — for rowid-PK test
3. **New test cases to add** (per RESEARCH §Test Pyramid `test_table.py` row):
   - `test_table_returns_200_feed_mode`
   - `test_table_tabular_fallback`
   - `test_facet_sidebar_renders`
   - `test_applied_facet_chip_renders`
   - `test_pagination_next_link_present_when_next_url`
   - `test_export_anchors_are_direct` (assert `href="/sglawwatch/headlines.csv"` in body, NOT a frontend-proxy path)
   - `test_hidden_table_blocked` (`/sglawwatch/_zeeker_schemas` → 404; `/sglawwatch/headlines_fts` → 404)
   - `test_unknown_table_returns_404`
   - `test_table_cache_control_header`
   - `test_table_italic_accent_h1`
   - `test_rowid_pk_fallback` (Pitfall 4)
   - `test_search_no_results_message` (`?_search=zzzzzz` → body contains "No results for")

**Anchor conventions:**
- `httpx.AsyncClient` with `transport=httpx.MockTransport(handler)` for the upstream mock.
- `httpx.AsyncClient` with `transport=httpx.ASGITransport(app=app)` for the FastAPI client.
- `app.state.http = _mock_datasette(...)` reassignment IN the fixture, with `await app.state.http.aclose()` in the `finally`.
- `@pytest.mark.asyncio` decorator on every test.
- `reset_metadata_cache()` autouse fixture clears the 60s TTL cache between tests.

---

### `tests/test_routes_row.py` (test, integration) — NEW

**Analog:** `packages/zeeker-frontend/tests/test_database.py` — same MockTransport+ASGITransport pattern.

Mirror everything from `test_routes_table.py`. Differences:
- Mock `/sglawwatch/headlines/{some-pk}.json` → returns `headlines_row` fixture.
- Test cases: `test_row_returns_200_article_mode`, `test_row_judgment_mode_renders_dateline`, `test_row_longform_no_aside`, `test_row_tabular_fallback_dl`, `test_row_long_text_uses_details`, `test_unknown_row_returns_404`, `test_row_cache_control_header`, `test_rowid_row_works` (Pitfall 4 integration coverage), `test_row_hidden_table_blocked`.

---

### `tests/test_urls.py` (test, unit) — NEW

**Analog:** `packages/zeeker-frontend/tests/test_filters.py`

**Class-grouped pure-function test pattern** (`test_filters.py:1-50`):
```python
"""Unit tests for zeeker_frontend.filters."""
from jinja2 import Undefined

from zeeker_frontend.filters import (
    filesizeformat, pluralize, safe_format, s, plural,
)


class TestFilesizeformat:
    def test_none_returns_dash(self):
        assert filesizeformat(None) == "—"

    def test_zero_bytes(self):
        assert filesizeformat(0) == "0 bytes"

    def test_kilobytes(self):
        assert filesizeformat(2048) == "2.0 KB"


class TestPluralize:
    def test_one_with_default_s(self):
        assert pluralize(1) == ""

    def test_two_with_default_s(self):
        assert pluralize(2) == "s"
```

**Mirror this exact structure** for urls.py:
```python
"""Unit tests for zeeker_frontend.urls."""
from zeeker_frontend.urls import (
    path_with_added_args, path_with_replaced_args, path_with_removed_args,
    set_sort, export_url, tilde_encode, row_url,
)

class TestPathWithAddedArgs: ...
class TestPathWithReplacedArgs: ...
class TestPathWithRemovedArgs: ...
class TestSetSort: ...    # cycles asc → desc → clear
class TestExportUrl: ...
class TestTildeEncode: ...    # /  → ~2F, %  → ~25, etc.
class TestRowUrl: ...    # compound pks comma-joined; empty pk_values → None or rowid fallback
```

**Anchor conventions:**
- No async — these are pure functions (no `@pytest.mark.asyncio`).
- No fixtures — pure-function tests only.
- Class-per-function grouping (`TestX:` → `def test_y(self):`) matches the existing test_filters.py style.

---

### `tests/test_datasette_client_table_row.py` (test, unit) — NEW

**Analog:** `packages/zeeker-frontend/tests/test_database.py:18-34` (the MockTransport handler block); but instead of driving the FastAPI app, drive `fetch_table` / `fetch_row` directly.

**Direct-call pattern:**
```python
import httpx, pytest
from zeeker_frontend.datasette_client import fetch_table, fetch_row

def _mock(handler):
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )

@pytest.mark.asyncio
async def test_fetch_table_filters_unknown_params():
    captured = {}
    def handler(req):
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rows": []})
    async with _mock(handler) as c:
        await fetch_table(c, "db", "tbl", {"_extras": "foo", "_size": "10", "category": "x"})
    assert "_extras" not in captured["params"]   # allowlist drops it
    assert captured["params"]["_size"] == "10"
    assert captured["params"]["category"] == "x"  # plain column passes
    assert captured["params"]["_shape"] == "objects"  # always added

@pytest.mark.asyncio
async def test_fetch_table_404_returns_none():
    async with _mock(lambda r: httpx.Response(404, json={})) as c:
        assert await fetch_table(c, "db", "tbl") is None

@pytest.mark.asyncio
async def test_fetch_table_500_raises():
    async with _mock(lambda r: httpx.Response(500, json={})) as c:
        with pytest.raises(httpx.HTTPError):
            await fetch_table(c, "db", "tbl")
```

Mirror for `fetch_row`. Test cases per RESEARCH §Test Pyramid `datasette_client.py` row.

---

### `scripts/verify_phase_05.sh` (verifier-script, sequential) — NEW

**Analog:** `scripts/verify_phase_04.sh` (verbatim shape).

**Header + topology delegation** (`verify_phase_04.sh:1-46`):
```bash
#!/usr/bin/env bash
# Phase X verifier — structural HTML + ...
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

BASE_URL="${BASE_URL:-http://localhost}"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0

echo "== Phase 5 verifier (BASE_URL=$BASE_URL) =="

# ===== A. Phase-4 invariants still hold =====
echo
echo "A. Phase-4 invariants (delegating to verify_phase_04.sh)"
if [ "$BASE_URL" = "http://localhost" ]; then
  if bash scripts/verify_phase_04.sh; then
    ok "verify_phase_04.sh passed"
  else
    fail "verify_phase_04.sh failed — see output above"
  fi
fi
```

**Body-fetch + grep pattern** (`verify_phase_04.sh:51-83`):
```bash
BODY=$(curl -fsS "$BASE_URL/sglawwatch/headlines" 2>/dev/null || echo "__CURL_FAIL__")
if echo "$BODY" | grep -q '__CURL_FAIL__'; then
  fail "curl to $BASE_URL/sglawwatch/headlines failed"
else
  echo "$BODY" | grep -q 'va-item' && ok "/sglawwatch/headlines contains .va-item" || fail "..."
  # cross-line H1 italic-accent (Phase-4 lesson):
  if echo "$BODY" | tr '\n' ' ' | grep -qE '<h1>[^<]*<em[^>]*>[^<]+</em>'; then
    ok "italic-accent H1 renders"
  else
    fail "missing italic-accent H1"
  fi
  # GET-based Cache-Control (Phase-4 lesson — HEAD returns 405 on @router.get):
  CC=$(curl -fsS -D - -o /dev/null "$BASE_URL/sglawwatch/headlines" 2>/dev/null | grep -i '^cache-control:' | tr -d '\r')
  if echo "$CC" | grep -qi 'max-age=60' && echo "$CC" | grep -qi 'stale-while-revalidate=300'; then
    ok "Cache-Control: max-age=60 + swr=300"
  else
    fail "Cache-Control missing or wrong: '$CC'"
  fi
fi
```

**Differences:** mirror sections A–O from RESEARCH §Phase 5 Verifier Script Outline (lines 850-935). Each section uses the same `BODY=$(curl ...)` + `echo "$BODY" | grep ...` shape with `ok` / `fail` helpers. The output `Phase 5 verifier: ALL GREEN` (vs `Phase 4 verifier: ALL GREEN`) is the only string change at the foot.

**Anchor conventions to preserve verbatim:**
- `set -euo pipefail` at top.
- `BASE_URL` defaulting to `http://localhost` so `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_05.sh` works for prod smoke.
- `tr '\n' ' '` before `grep -qE` for any HTML pattern that spans lines (Phase-4 fix lesson).
- `curl -fsS -D - -o /dev/null` for header reads; `curl -fsS` for body reads — never `curl -I` (HEAD), which uvicorn returns 405 for `@router.get` routes.
- Negative assertions use plain `grep -q '_zeeker'` then invert with `if/else fail` (the `|| true` plus `FAILED=1` aggregation pattern from `verify_phase_04.sh:27`).
- Final exit code: `if [ "$FAILED" -eq 0 ]; then exit 0; else exit 1; fi`.

---

## Shared Patterns

### S1. Lifespan-scoped HTTP client + app.state.templates

**Source:** `packages/zeeker-frontend/src/zeeker_frontend/main.py:38-82`

**Apply to:** every new route handler (`routes_table.py`, `routes_row.py`).

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        base_url=DATASETTE_URL,
        timeout=httpx.Timeout(10.0, connect=2.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    try:
        yield
    finally:
        await app.state.http.aclose()
# ...
app.state.templates = templates
```

**In handler — always:**
```python
client: httpx.AsyncClient = request.app.state.http
# render via:
request.app.state.templates.TemplateResponse(request=request, name="...", context={...})
```

**Never:** import `templates` directly into a route module (circular-import trap — the comment at `main.py:80-82` explicitly calls this out).

### S2. Cache-Control on every HTML response

**Source:** `routes_database.py:71` and `routes_home.py:57`

**Apply to:** every new HTML route handler (table + row).

```python
response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
return response
```

**Verifier-load-bearing string** — `verify_phase_04.sh:78-82` and `verify_phase_05.sh` will both grep for `max-age=60` and `stale-while-revalidate=300`. Any deviation breaks the verifier.

### S3. 503 on httpx error, 404 on missing data — never 500

**Source:** `routes_database.py:20-27`

**Apply to:** every fetch in every route handler.

```python
try:
    payload = await fetch_table(client, db, table, ...)
except httpx.HTTPError:
    raise HTTPException(status_code=503, detail="Data API unavailable")
if payload is None:
    raise HTTPException(status_code=404, detail="Table not found")
```

This is the load-bearing pattern that prevents 500-traceback disclosure (RESEARCH §Security `V7 Errors and Logging`).

### S4. Hidden-table guard at route boundary (Phase 5 NEW shared rule)

**Source:** none in Phase 4 (Phase 4 only filters at the database list level). NEW for Phase 5.

**Apply to:** both `routes_table.py` and `routes_row.py` — the FIRST thing the handler does after path-param parsing.

```python
_HIDDEN_TABLE_PREFIXES = ("_zeeker",)
_HIDDEN_TABLE_SUFFIXES = ("_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config")

if table.startswith(_HIDDEN_TABLE_PREFIXES) or table.endswith(_HIDDEN_TABLE_SUFFIXES):
    raise HTTPException(status_code=404, detail="Table not found")
```

**Why both prefix AND suffix** — RESEARCH Pitfall 6 + the Phase-4 fix at commit `f5fb2f9`. Datasette's `hidden=true` flag covers FTS internals on the database-page payload, but if the table-page handler skips that flag (it's per-table, not in the database payload), direct URLs to `_zeeker_schemas` or `headlines_fts` would leak data. Both checks together close the gap.

### S5. Italic-accent H1 split at last whitespace

**Source:** `database.html:22-30`

**Apply to:** every page-level H1 (table + row).

```jinja
{% if ' ' in db_title %}
  {% set idx = db_title.rfind(' ') %}
  {{ db_title[:idx] }} <em>{{ db_title[idx+1:] }}</em>
{% else %}
  <em>{{ db_title }}</em>
{% endif %}
```

**Verifier-load-bearing pattern** — `verify_phase_04.sh:62, 112` greps for `<h1>...<em>...</em>...</h1>` after `tr '\n' ' '` collapse. Skipping the rfind split breaks verifier section B/C/J.

### S6. Defensive Jinja metadata access (Starlette strict mode)

**Source:** `database.html:121` — `{% set table_meta = (metadata.tables[table.name] if metadata and metadata.tables and table.name in metadata.tables else {}) %}`

**Apply to:** any nested metadata lookup in templates.

The defensive guard avoids `KeyError` under Starlette's strict-Jinja mode. Pre-computing in the handler and passing pre-resolved dicts (e.g. `display = table_meta.get("display") or {}` in Python) is the **preferred** pattern; do the lookup once in Python, keep templates thin.

### S7. MockTransport + ASGITransport test pyramid

**Source:** `tests/test_database.py:18-47` and `tests/conftest.py:42-64`.

**Apply to:** both `test_routes_table.py` and `test_routes_row.py`.

Two-layer transport: outer `httpx.AsyncClient` driving the FastAPI app via `ASGITransport`; inner `app.state.http` swapped to a `MockTransport` returning fixture JSON. No docker required. Same `reset_metadata_cache` autouse fixture pattern.

### S8. Self-hosted-fonts / no-Google-Fonts / safe_format / Inter-Fraunces-JetBrains lock

**Source:** `CLAUDE.md` §Architecture + `zeeker.css:85-135` token table.

**Apply to:** every CSS authoring decision.

No new font imports; no new CSS variables; every `--*` token used in Phase-5 CSS must already be defined at `zeeker.css:1-368` (`:root`).

### S9. Suffix routing for exports (D-05 LOCKED)

**Source:** `database.html:54-59` (existing export anchors at the database level) + `Caddyfile`/`Caddyfile.prod` `@datasette` matcher (Phase 3).

**Apply to:** every export anchor in `table.html` and `row.html`.

```jinja
<a href="/{{ database }}/{{ table }}.csv?{{ request_qs }}">CSV ↗</a>
<a href="/{{ database }}/{{ table }}.json?{{ request_qs }}">JSON ↗</a>
```

**Verifier-load-bearing** — `verify_phase_05.sh` section I asserts the body contains these literal `href=` values AND that `curl -I /{db}/{table}.csv` returns a Caddy-routed `text/csv` response (NOT a frontend route). Never proxy CSV/JSON through FastAPI.

---

## No Analog Found

These files have no direct in-repo analog. The planner should rely on RESEARCH excerpts + UI-SPEC + sketch references rather than searching for a closer match.

| File | Role | Reason | Author from |
|------|------|--------|-------------|
| `urls.py` | utility | No querystring helpers exist anywhere in `packages/zeeker-frontend/` yet | Direct port from `.venv/lib/python3.12/site-packages/datasette/utils/__init__.py:268-331, 1173-1186`. RESEARCH §Pattern 2 already includes the verbatim port body. |
| `templates/_partials/facet_sidebar.html` | partial | No existing facet UI in the frontend (Phase 4 had no facet sidebar) | UI-SPEC §`/{db}/{table}` → Toolbar contents + Facets sidebar; sketch `references/directory-and-feed-lists.md:117-127` |
| `templates/_partials/pagination.html` | partial | No existing pagination component | UI-SPEC §Pagination (all modes) — `← Previous` / `Next →` links from `next_url` + page-size selector `?_size={25,50,100}` |
| `templates/_partials/applied_facets.html` | partial | No existing chip / pill component | UI-SPEC §Applied-facet chips — `.filter-chip` with `×` clear link |
| `templates/_partials/row_judgment.html` | partial | No editorial broadsheet layout exists | UI-SPEC §`row_mode: judgment` + sketch `references/row-reading-layouts.md` (judgment broadsheet section) |
| `templates/_partials/row_article.html` | partial | No magazine-article layout exists | UI-SPEC §`row_mode: article` + sketch `references/row-reading-layouts.md` (sketch 003-A magazine variant) |

**Note on partials directory creation:** the `_partials/` subdirectory does not exist yet under `packages/zeeker-frontend/src/zeeker_frontend/templates/`. The plan should create it (and document it in plan front-matter `key_files.created`). Jinja `{% include "_partials/..." %}` resolves relative to the `templates/` root configured in `main.py:70`, so no extra `searchpath` config is needed.

---

## Metadata

**Analog search scope:**
- `packages/zeeker-frontend/src/zeeker_frontend/` — primary (Phase 4 outputs)
- `packages/zeeker-frontend/tests/` — test analogs
- `templates/` (M1 reference, root) — slot-mapping reference only, NOT to copy verbatim
- `static/css/zeeker-base.css` (M1 reference) — feed-card CSS harvest source
- `scripts/verify_phase_04.sh` — verifier shape
- `metadata.json` — config edit shape

**Files scanned:** 23 (15 Phase-4 frontend files, 4 M1 reference templates, 1 M1 CSS, 1 metadata.json, 1 verifier script, 1 Phase-4 SUMMARY chain)

**Pattern extraction date:** 2026-04-25

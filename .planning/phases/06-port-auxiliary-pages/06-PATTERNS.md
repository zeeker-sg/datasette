# Phase 6: Port auxiliary pages — Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 30 (20 new + 4 modified + 6 new test/fixtures)
**Analogs found:** 28 / 30

Phase 6 is mostly a 1:1 port: every new Python module already has a Phase 4-5 sibling that locks the route-handler shape, every aux template inherits the existing `base.html` shell, and every CSS subsection is harvested from M1's `static/css/zeeker-base.css` with body-class scoping. The two surfaces that have *no* analog (`changelog.py` YAML loader, `_param_*` allowlist for `/sql`) are explicitly called out below.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `routes_aux.py` (new) | route handler | request-response | `routes_database.py` | exact |
| `routes_search.py` (new) | route handler | request-response (fan-out) | `routes_table.py` + `routes_home.py` | role-match |
| `routes_sql.py` (new) | route handler | request-response (POST + GET) | `routes_database.py` + `routes_table.py` | role-match |
| `changelog.py` (new) | utility (boot loader) | file-I/O | `datasette_client.py` cache helpers | partial |
| `data/changelog.yaml` (new) | config / data | file-I/O | `plugins/strings.yaml` recent_updates block | exact (M1 source) |
| `templates/pages/about.html` (new) | template | server-render | `templates/pages/about.html` (M1) + `database.html` (frontend) | exact |
| `templates/pages/how-to-use.html` (new) | template | server-render | `templates/pages/how-to-use.html` (M1) + `database.html` (frontend) | exact |
| `templates/pages/sources.html` (new) | template | server-render | `templates/pages/sources.html` (M1) | exact |
| `templates/pages/status.html` (new) | template | server-render | `templates/pages/status.html` (M1) | exact |
| `templates/pages/developers.html` (new) | template | server-render | `templates/pages/developers.html` (M1) | exact |
| `templates/pages/search.html` (new) | template | server-render | `templates/_partials/table_feed.html` + `applied_facets.html` | role-match |
| `templates/pages/sql_index.html` (new) | template | server-render | `database.html` (frontend) `.list .row` editorial pattern | role-match |
| `templates/pages/sql_db.html` (new) | template | server-render (POST result) | `templates/pages/how-to-use.html` `.example-box` + frontend `table.html` | partial |
| `templates/llms.txt` (new) | template | server-render (text/plain) | `plugins/developers_page.py:81-115` | exact (no Jinja analog) |
| `templates/_partials/api_table.html` (new) | partial | server-render | `templates/_partials/applied_facets.html` | role-match |
| `templates/_partials/method_card.html` (new) | partial | server-render | `templates/_partials/applied_facets.html` | role-match |
| `templates/_partials/example_box.html` (new) | partial | server-render | `templates/pages/how-to-use.html` `.example-box` (M1) | exact |
| `templates/_partials/search_result.html` (new) | partial | server-render | `templates/_partials/table_feed.html` `.va-item` block | role-match |
| `templates/_partials/timeline_item.html` (new) | partial | server-render | `templates/pages/status.html` `.timeline-item` (M1) | exact |
| `static/robots.txt` (new) | static asset | file-I/O | `templates/pages/robots.txt` (M1) | exact (verbatim copy) |
| `static/css/zeeker.css` (modified) | stylesheet | append-only | `static/css/zeeker-base.css` lines 700-2900 (M1) | exact |
| `static/js/aux.js` (new — Discretion) | JS utility | event-driven | (no analog — vanilla 8-line snippet) | none |
| `main.py` (modified) | bootstrap | startup-once | `main.py` Phase-4 lifespan | exact (extension only) |
| `datasette_client.py` (modified) | http client | request-response | `datasette_client.py:74-99` (`fetch_table`) | exact |
| `pyproject.toml` (modified) | config | declaration | (existing `[project] dependencies`) | exact |
| `tests/test_routes_aux.py` (new) | test | request-response | `tests/test_database.py` | exact |
| `tests/test_routes_search.py` (new) | test | request-response | `tests/test_routes_table.py` | exact |
| `tests/test_routes_sql.py` (new) | test | request-response (POST) | `tests/test_routes_table.py` | role-match |
| `tests/test_datasette_client_phase06.py` (new) | test | request-response (unit) | `tests/test_datasette_client_table_row.py` | exact |
| `tests/test_changelog.py` (new) | test | file-I/O | (no analog — pure unit test of module) | partial |
| `tests/fixtures/*.json` (new — 4 files) | test data | file-I/O | `tests/fixtures/sglawwatch.json` etc. | exact |
| `scripts/verify_phase_06.sh` (new) | shell verifier | shell-script | `scripts/verify_phase_05.sh` | exact |

---

## Pattern Assignments

### `routes_aux.py` (route handler, request-response)

**Analog:** `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py`

**Imports + router setup pattern** (`routes_database.py:1-12`):
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

For `routes_aux.py`, add `PlainTextResponse, FileResponse` imports for `/llms.txt` and `/robots.txt`, and `from pathlib import Path` for the static-file path. Each handler is its own `@router.get(...)` — six total: `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/robots.txt`.

**Core handler pattern — fetch + 503 + 404 + render** (`routes_database.py:15-72`):
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
        raise HTTPException(status_code=404, detail="Database not found")

    visible_tables = [
        t for t in payload.get("tables", [])
        if not t.get("hidden") and not t.get("name", "").startswith("_zeeker")
    ]

    site_metadata = await fetch_site_metadata(client)
    db_entry = (site_metadata.get("databases") or {}).get(db) or {}

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="database.html",
        context={
            "database": db,
            "tables": visible_tables,
            ...
            "breadcrumbs": [{"label": breadcrumb_label}],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

**Apply to:** `/developers`, `/sources`, `/status`, `/about`, `/how-to-use` — replace the per-handler data shape (e.g. status uses `app.state.changelog`, sources iterates databases). Pass `page_class="page-{slug}"` and `breadcrumbs=[{"label": "..."}]` for every handler. `Cache-Control` is mandatory on every response.

**Hidden-table predicate** (`routes_database.py:33-36`) — apply to `/sources`, `/developers`, `/llms.txt`:
```python
visible_tables = [
    t for t in payload.get("tables", [])
    if not t.get("hidden") and not t.get("name", "").startswith("_zeeker")
]
```

**`/llms.txt` PlainTextResponse pattern** (RESEARCH §Pattern 5, no codebase analog):
```python
from fastapi.responses import PlainTextResponse

@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt(request: Request):
    client = request.app.state.http
    try:
        dbs = await fetch_databases(client)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")
    # ... build db_blocks, render the .txt template ...
    body = request.app.state.templates.get_template("llms.txt").render(databases=db_blocks)
    response = PlainTextResponse(content=body, media_type="text/plain; charset=utf-8")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

**`/robots.txt` static-file pattern** (RESEARCH §Pitfall 13):
```python
_STATIC_DIR = Path(__file__).parent / "static"

@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return PlainTextResponse(
        (_STATIC_DIR / "robots.txt").read_text(),
        media_type="text/plain; charset=utf-8",
    )
```

---

### `routes_search.py` (route handler, fan-out)

**Analog:** `packages/zeeker-frontend/src/zeeker_frontend/routes_table.py` (handler shape) + RESEARCH §Pattern 1 (fan-out specifics)

**Auth/guard pattern (none — public read)** — same as Phase 4-5; no auth middleware in this codebase.

**Core fan-out pattern** (RESEARCH §Pattern 1; no exact codebase analog):
```python
import asyncio

async def _safe_search_one(client, db, table, q, size):
    try:
        r = await client.get(
            f"/{db}/{table}.json",
            params={"_search": q, "_size": size, "_shape": "objects"},
            timeout=httpx.Timeout(3.0, connect=1.0),
        )
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError):
        return None  # caller treats None as "table errored"

@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", _retry: int = 0):
    client = request.app.state.http
    searchable: dict[str, list[str]] = request.app.state.searchable_tables
    if not q.strip():
        # State A — render hero search + tips, no fan-out
        ...
    pairs = [(db, t) for db, ts in searchable.items() for t in ts]
    tasks = [_safe_search_one(client, db, t, q, 10) for db, t in pairs]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Group + sort + render
    ...
```

**Why `gather(return_exceptions=True)` not `TaskGroup`** — RESEARCH §Pitfall 2: TaskGroup cancels siblings on first failure. One slow table would empty `/search`. Use `gather`.

**Cache-Control + breadcrumb pattern** (`routes_table.py:115-130`):
```python
response = request.app.state.templates.TemplateResponse(
    request=request,
    name="pages/search.html",
    context={
        ...
        "breadcrumbs": [{"label": "Search"}],
        "page_class": "page-search",
        "current_year": datetime.now().year,
    },
)
response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
return response
```

**503 fallback** (RESEARCH §Pitfall 10): if `searchable_tables == {}` AND `q` non-empty, raise `HTTPException(503, "Search temporarily unavailable. Try again in a minute.")`. State A (empty `q`) always renders.

---

### `routes_sql.py` (route handler, GET + POST)

**Analog:** `routes_database.py` (GET shape) + `routes_table.py` (querystring allowlist) + RESEARCH §Pattern 4 (POST + 400-handling)

**GET handler — landing list** (mirror `routes_database.py:15-72` but iterate the database list, not one db):
```python
from zeeker_frontend.datasette_client import fetch_databases, fetch_site_metadata

@router.get("/sql", response_class=HTMLResponse)
async def sql_index(request: Request):
    client = request.app.state.http
    try:
        databases = await fetch_databases(client)
    except httpx.HTTPError:
        raise HTTPException(503, "Data API unavailable")
    visible_dbs = [d for d in databases if not d.get("hidden")]
    site_metadata = await fetch_site_metadata(client)
    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="pages/sql_index.html",
        context={
            "databases": visible_dbs,
            "metadata": site_metadata,
            "breadcrumbs": [{"label": "SQL"}],
            "page_class": "page-sql",
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

**GET `/sql/{db}` editor (no execution)** — mirror `routes_database.py` 404 path; pass `sql=request.query_params.get("sql")` for shareable URL pre-fill, do NOT execute. Compute canned-queries from site_metadata (RESEARCH §Code Examples):
```python
def get_canned_queries(site_metadata: dict, db: str) -> dict[str, dict]:
    return ((site_metadata.get("databases") or {}).get(db) or {}).get("queries") or {}
```

**POST handler — Form body + 400-aware error handling** (RESEARCH §Pattern 4):
```python
import re
from fastapi import Form

_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")

def _detect_params(sql: str) -> list[str]:
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
    ds_params = {"sql": sql, "_shape": "objects"}
    for name in _detect_params(sql):
        if name in param_values:
            ds_params[f"_param_{name}"] = param_values[name]
    error, results = None, None
    try:
        r = await client.get(f"/{db}.json", params=ds_params)
        body = r.json()
        if r.status_code == 400:
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
        context={"database": db, "sql": sql, "results": results, "error": error,
                 "page_class": "page-sql-db", ...},
    )
    response.headers["Cache-Control"] = "no-store"   # D-14
    return response
```

**Querystring allowlist** — analog from `datasette_client.py:68-71` `_TABLE_ALLOWED_PARAMS`. For `/sql`, the allowlist is implicit: only `sql` and detected `:param` names are forwarded; everything else in the form is dropped.

**Error response shape** — RESEARCH §Pitfall 1: SQL errors are HTTP 400 (not 200), and the body has a populated `error` field. NEVER `raise_for_status()` before inspecting the body on 400.

---

### `changelog.py` (utility, boot loader)

**Analog:** `datasette_client.py` cache-helper pattern (`fetch_site_metadata` + `reset_metadata_cache`); RESEARCH §Pattern 3 for the YAML specifics.

**Core loader** (RESEARCH §Pattern 3 — no direct codebase analog, partial structural match to `datasette_client.py:14-15`):
```python
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

**What's preserved:** module-level `_DATA_DIR` cached path (mirrors `datasette_client.py:14`); pure function (no class); empty-fallback degradation pattern (mirrors `fetch_site_metadata` returning `{}` on transport error).

**What's new:** `yaml.safe_load` (new dep — `pyyaml>=6.0,<7.0` in `pyproject.toml`); single-shot at boot, no TTL.

---

### `data/changelog.yaml` (config / data)

**Analog:** `plugins/strings.yaml` lines 78-86 (M1 source). Verbatim port:

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

Schema unchanged from M1: `date` (ISO string), `type` (one of `feature|data|technical|bugfix`), `title`, `description`.

---

### `templates/pages/{about,how-to-use,sources,status,developers}.html` (Jinja templates)

**Analog 1:** M1 templates `templates/pages/{name}.html` (the data shape + section ordering)
**Analog 2:** `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` (the frontend extends pattern + breadcrumb + body class)

**Imports/extends pattern** (`database.html:1-9`):
```jinja
{% extends "base.html" %}

{% block head %}
{% if metadata and metadata.description %}
<meta name="description" content="{{ metadata.description }}">
{% endif %}
{% endblock %}

{% block content %}
...
{% endblock %}
```

**M1 → frontend port rules** (RESEARCH §State of the Art):
- M1 `{% extends "default:base.html" %}` → frontend `{% extends "base.html" %}` (drop `default:` namespace)
- M1 `{% block nav %}{% include "_header.html" %}{% endblock %}` → DELETE (frontend `base.html` already renders nav)
- M1 `{% block footer %}{% include "_footer.html" %}{% endblock %}` → DELETE (same — frontend `base.html` renders footer)
- M1 `{{ s('key') }}` template helper still works — `filters.py.s()` is registered as a Jinja global in Phase 4 `main.py:77-78`
- M1 `<a href="/-/metadata">` in `about.html` → re-point to `/developers` (RESEARCH §State of the Art; UI-SPEC §Copywriting)
- M1 `<a href="/-/search">` references in `how-to-use.html` → re-point to `/search` (UI-SPEC §Footer Link Carry-Forward)

**Italic-accent H1** (`database.html:21-30`, applies to every aux page per D-16):
```jinja
<h1>
  {% set page_title = "About Zeeker" %}  {# example for /about #}
  {% if ' ' in page_title %}
    {% set idx = page_title.rfind(' ') %}
    {{ page_title[:idx] }} <em>{{ page_title[idx+1:] }}</em>
  {% else %}
    <em>{{ page_title }}</em>
  {% endif %}
</h1>
```

UI-SPEC §Copywriting locks each H1 — e.g. `Developer <em>portal</em>`, `Recent <em>updates</em>`, `Data <em>sources</em>`, `About <em>Zeeker</em>`, `How to use <em>this site</em>`. Templates can hard-code the `<em>` markup directly (since the copy is fixed), no fancy split logic needed.

**Hidden-table filter in templates** (`database.html` — same predicate as handler, applied in `/sources` per-table preview):
```jinja
{% for table in database.tables[:5] %}
{% if not table.name.startswith('_zeeker') %}
<li>...</li>
{% endif %}
{% endfor %}
```

---

### `templates/pages/search.html` (Jinja template, two states)

**Analog:** `templates/_partials/table_feed.html` (the `.va-item` card pattern) + `templates/_partials/applied_facets.html` (the "active filter chip" pattern reused as the `× clear` link)

**State A (empty q) + State B (results) in one template — pseudo-shape per UI-SPEC §`/search`:**
```jinja
{% extends "base.html" %}
{% block content %}
<div class="container">
  <header class="search-hero guide-hero">
    <div class="kicker">№ 01 · SEARCH</div>
    {% if q %}
      <h1>Results for <em>{{ q|e }}</em></h1>
    {% else %}
      <h1>Search across <em>everything</em></h1>
    {% endif %}
    <form class="search-form" method="get" action="/search" role="search">
      <input type="search" name="q" value="{{ q|e }}" placeholder="Search FTS-indexed tables…" autocomplete="off">
      <button type="submit">Search</button>
      {% if q %}<a class="search-clear" href="/search">× Clear</a>{% endif %}
    </form>
    {% if q %}
      <p class="lede">{{ total_count }} results across {{ n_databases }} databases</p>
    {% endif %}
  </header>

  {% if not q %}
    <section class="aux-card search-tips"> ... tips ul ... </section>
  {% elif total_count == 0 %}
    <section class="aux-card search-empty"> ... no-results copy ... </section>
  {% else %}
    {% for group in groups %}
      <section class="search-group" id="group-{{ group.db }}-{{ group.table }}">
        <header class="search-group-head">
          <h2><a href="/{{ group.db }}/{{ group.table }}?_search={{ q|urlencode }}">{{ group.db }} › {{ group.table }}</a></h2>
          <span class="result-count">{{ group.count }} {{ group.count|pluralize('result') }}</span>
        </header>
        <ol class="search-results">
          {% for row in group.rows %}
            {% include "_partials/search_result.html" %}
          {% endfor %}
        </ol>
        {% if group.count > 10 %}
          <a class="see-all" href="/{{ group.db }}/{{ group.table }}?_search={{ q|urlencode }}">See all {{ group.count }} results →</a>
        {% endif %}
      </section>
    {% endfor %}
  {% endif %}
</div>
{% endblock %}
```

**Result card pattern** — port from `templates/_partials/table_feed.html` (which defines `.va-item`, `.va-item-head`, `.va-item-title`, `.va-item-excerpt`, `.va-item-foot`). `_partials/search_result.html` mirrors the structure with tighter spacing (UI-SPEC §`.search-result` Component Inventory).

---

### `templates/pages/sql_index.html` and `templates/pages/sql_db.html`

**Analog `sql_index.html`:** `database.html` editorial-row pattern (`database.html:114-158` `<div class="list">` with `<div class="row">` items — apply to database list).

**Editorial-row port** (frontend `database.html:120-156`):
```jinja
<div class="list">
  {% for database in databases %}
  <div class="row">
    <div class="idx">{{ "{:02d}".format(loop.index) }}</div>
    <div class="name-col">
      <a href="/sql/{{ database.name }}" class="name">{{ database.name|title }}</a>
    </div>
    <div class="cols"></div>
    <div class="count-col">
      <span class="count">{{ database.tables_count }}</span>
      <span class="label">{{ plural(database.tables_count, 'plural_table', 'plural_tables') }}</span>
    </div>
  </div>
  {% endfor %}
</div>
```

**Analog `sql_db.html`:** RESEARCH §Code Examples (`<details>` + canned-query `<button>` list) + `templates/pages/how-to-use.html` `.example-box` pattern for the textarea. No exact codebase analog.

**Canned-queries `<details>` pattern** (RESEARCH §Code Examples):
```jinja
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

**Form + results region** (mirror frontend `table.html` structure for results table; harvest `.example-box` for textarea). Export anchors mirror Phase 5 D-05 pattern (frontend `table.html:55-58` `.export-links`):
```jinja
<a href="/{{ database }}.csv?sql={{ sql|urlencode }}">Download CSV ↗</a>
<a href="/{{ database }}.json?sql={{ sql|urlencode }}">View JSON ↗</a>
```

---

### `templates/llms.txt` (Jinja text/plain — no autoescape)

**Analog:** `plugins/developers_page.py:81-115` (the canonical body shape)

**Pattern** (RESEARCH §Pattern 5 + Pitfall 8):
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

**Anti-pattern (Pitfall 8):** never use `|e` in this template; Starlette's `Jinja2Templates` only auto-escapes `.html/.htm/.xml` so `.txt` is correctly off — adding `|e` re-introduces HTML entity encoding.

---

### `templates/_partials/*.html` (Discretion split)

**Analog:** `templates/_partials/applied_facets.html`, `templates/_partials/table_feed.html`, `templates/_partials/pagination.html` — Phase 5 partials all use plain Jinja `{% include %}` (no macros, no inheritance) and read context from the parent scope.

**Pattern** (`templates/_partials/applied_facets.html` — read from parent context):
```jinja
{% if applied_filters or active_search %}
<div class="filter-chips">
  {% if active_search %}
    <a class="filter-chip filter-chip-search" href="...">
      <strong>Search:</strong> {{ active_search }}
      <span class="x">×</span>
    </a>
  {% endif %}
  ...
</div>
{% endif %}
```

**New partials Phase 6 splits out (Discretion):**
- `_partials/api_table.html` — 2-col API parameter table (used twice on `/developers`)
- `_partials/method_card.html` — numbered method card (used by `/about` + `/how-to-use`)
- `_partials/example_box.html` — `<pre><code>` + copy button (used by `/how-to-use` + `/developers`)
- `_partials/search_result.html` — single FTS hit row (used by `/search`)
- `_partials/timeline_item.html` — status update row (used by `/status`)

All are plain `{% include "_partials/X.html" %}` calls; no macro args needed.

---

### `static/robots.txt` (verbatim copy)

**Analog:** `templates/pages/robots.txt` (M1) — 35 lines verbatim. No transformation.

```
User-agent: GPTBot
Disallow: /

User-agent: OAI-SearchBot
Disallow: /
... (33 more lines, copy verbatim) ...
# Content signals (EU DSM Directive Article 4)
#
# search:   yes
# ai-input: no
# ai-train: no
```

URL routes through `routes_aux.py` `@router.get("/robots.txt")` (RESEARCH §Pitfall 13 — single FileResponse, NOT `StaticFiles`-mounted, so URL is `/robots.txt` not `/static/robots.txt`).

---

### `static/css/zeeker.css` (modified — append-only)

**Analog:** `static/css/zeeker-base.css` lines 700-2900 (M1). UI-SPEC §CSS Harvest enumerates the exact line ranges per subsection.

**Insertion point** (existing `static/css/zeeker.css:1716`):
```css
/* =========== END phase 05 ============ */

/* INSERT PHASE 6 CONTENT HERE */
/* =========== AUXILIARY PAGES — phase 06 ============ */
... harvested subsections, body-class scoped ...
/* =========== END phase 06 ============ */

/* =======================================================
   FOOTER LINK OVERRIDE — must remain at TAIL of file
   ======================================================= */
```

**Body-class scoping pattern** (M1 lines 2678+, 2802+, etc.):
```css
.page-status .stats-simple { ... }
.page-status .timeline-item { ... }
.page-developers .api-table { ... }
.page-sources .database-meta { ... }
```

**M1 token mapping** — M1 uses some legacy token names that the frontend's `:root` has renamed. Substitution table:
| M1 token | Frontend token (use this) |
|----------|---------------------------|
| `--color-bg-surface` | `--color-surface` |
| `--color-bg-tertiary` | `--color-bg-alt` |
| `--color-surface-sunken` | `--color-bg-alt` |
| `--color-text-primary` | `--color-ink` |
| `--color-text-muted` | `--color-text-muted` (same) |
| `--color-accent-primary` | `--color-accent` |
| `--space-xs/sm/md/lg/xl/2xl/3xl` | `--space-1/2/3/4/5/6/8/10/12` (4px scale) |
| `--text-xs/sm/base/lg/xl/2xl/3xl` | same names exist |
| `--font-display/mono/body` | same names exist |
| `--radius-sm/md/lg/xl` | same names exist |
| `--transition-base/fast` | author inline `transition: <prop> 0.15s ease` |

**Drop:** All `.token.*` Prism rules (M1 lines 986-1046) — no syntax highlighter ships in v1 (D-09).

---

### `static/js/aux.js` (new, optional — Discretion)

**Analog:** none. RESEARCH §Code Examples — 8-line vanilla snippet, no dependencies:
```js
document.querySelectorAll(".canned-query").forEach(btn => {
  btn.addEventListener("click", () => {
    const ta = document.querySelector("textarea[name=sql]");
    if (ta) { ta.value = btn.dataset.sql; ta.focus(); }
  });
});

document.querySelectorAll(".copy-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const pre = btn.parentElement.querySelector("pre");
    if (pre) navigator.clipboard.writeText(pre.innerText).then(() => {
      btn.classList.add("copied"); btn.textContent = "Copied";
      setTimeout(() => { btn.classList.remove("copied"); btn.textContent = "Copy"; }, 1500);
    });
  });
});
```

Loaded via `<script defer src="/static/js/aux.js"></script>` in `base.html` (one-line edit) OR inline in `sql_db.html`/`how-to-use.html` only (planner picks).

---

### `main.py` (modified — extension only)

**Analog:** existing `main.py` (`packages/zeeker-frontend/src/zeeker_frontend/main.py`)

**Lifespan extension pattern** (existing `main.py:38-51`):
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
```

**Phase 6 extension** (RESEARCH §Pattern 2):
```python
from zeeker_frontend.datasette_client import discover_searchable_tables
from zeeker_frontend.changelog import load_changelog

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(...)  # existing
    # NEW: one-shot probe at boot; cached for process lifetime (D-04)
    app.state.searchable_tables = await discover_searchable_tables(app.state.http)
    # NEW: changelog loaded once at boot (D-12)
    app.state.changelog = load_changelog()
    try:
        yield
    finally:
        await app.state.http.aclose()
```

**Router registration order** (RESEARCH §Pitfall 3 — load-bearing). Existing order:
```python
app.include_router(home_router)
app.include_router(database_router)   # /{db} catch-all
app.include_router(table_router)      # /{db}/{table}
app.include_router(row_router)        # /{db}/{table}/{pk}
```

**Phase 6 ordering — new routers MUST come before `database_router`:**
```python
app.include_router(home_router)
app.include_router(aux_router)        # NEW — /developers, /status, /sources, /about, /how-to-use, /llms.txt, /robots.txt
app.include_router(search_router)     # NEW — /search
app.include_router(sql_router)        # NEW — /sql, /sql/{db}
app.include_router(database_router)   # /{db} CATCH-ALL — must remain last among single-segment matchers
app.include_router(table_router)
app.include_router(row_router)
```

**One-line nav edit** (`base.html:61`): `<a href="/-/search">Search</a>` → `<a href="/search">Search</a>`. UI-SPEC §Footer Link Carry-Forward.

---

### `datasette_client.py` (modified — extension only)

**Analog:** existing `datasette_client.py:74-99` (`fetch_table` — allowlist + `_shape=objects` + 404 handling)

**Existing `fetch_table` pattern** (`datasette_client.py:74-99`):
```python
async def fetch_table(client, db, table, params=None):
    safe_params: dict[str, Any] = {"_shape": "objects"}
    for k, v in (params or {}).items():
        if k in _TABLE_ALLOWED_PARAMS:
            safe_params[k] = v
        elif "__" in k:           # column__exact, column__contains
            safe_params[k] = v
        elif not k.startswith("_"):  # plain column-name filters
            safe_params[k] = v
    r = await client.get(f"/{db}/{table}.json", params=safe_params)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
```

**Phase 6 additions:**

**`discover_searchable_tables`** (RESEARCH §Pattern 2 — uses verified live `fts_table` field):
```python
async def discover_searchable_tables(client: httpx.AsyncClient) -> dict[str, list[str]]:
    """Return {db_name: [table_names_with_fts]}. One-shot at lifespan boot.

    Live-verified: each /{db}.json table dict has `fts_table` (string or None).
    """
    out: dict[str, list[str]] = {}
    try:
        dbs = await fetch_databases(client)
    except httpx.HTTPError:
        return out
    for entry in dbs:
        db = entry["name"]
        try:
            payload = await fetch_database(client, db)
        except httpx.HTTPError:
            continue
        if payload is None:
            continue
        names = []
        for t in payload.get("tables") or []:
            if t.get("hidden") or t.get("name", "").startswith("_zeeker"):
                continue
            if t.get("fts_table"):
                names.append(t["name"])
        if names:
            out[db] = names
    return out
```

**`search_table`** (RESEARCH §Code Examples — wraps `/{db}/{table}.json?_search=...`):
```python
async def search_table(client, db, table, q, size=10):
    r = await client.get(
        f"/{db}/{table}.json",
        params={"_search": q, "_size": size, "_shape": "objects"},
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
```

**`execute_sql`** (RESEARCH §Code Examples — handles 400 + populated `error`):
```python
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

**Anti-pattern preserved (Pitfall 1):** check `r.status_code == 404` BEFORE `raise_for_status()`. Same idiom as `fetch_database:36-39`.

---

### `pyproject.toml` (modified — add dep)

**Analog:** existing `[project] dependencies` block in `packages/zeeker-frontend/pyproject.toml` (verified RESEARCH §Standard Stack).

**Pattern (additive only):**
```toml
dependencies = [
    "fastapi[standard]==0.136.0",
    "httpx==0.28.1",
    "jinja2==3.1.6",
    "uvicorn[standard]==0.44.0",
    "pyyaml>=6.0,<7.0",   # NEW — Phase 6 D-12 changelog loader
]
```

**Anti-pattern (Pitfall 12):** do NOT rely on the system PyYAML. Container build uses a clean uv-installed venv; the dep MUST be declared.

---

### `tests/test_routes_aux.py` (new — integration test)

**Analog:** `tests/test_database.py` (Phase 4 integration test — full ASGITransport + MockTransport round trip)

**Imports + fixture pattern** (`test_database.py:1-48`):
```python
"""Route tests for GET /{db} — MockTransport exercises the full stack."""
from __future__ import annotations

import httpx
import pytest

from zeeker_frontend.main import app
from zeeker_frontend.datasette_client import reset_metadata_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_metadata_cache()
    yield
    reset_metadata_cache()


def _mock_datasette(sglawwatch_fixture, metadata_fixture):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/sglawwatch.json":
            return httpx.Response(200, json=sglawwatch_fixture)
        if path == "/-/metadata.json":
            return httpx.Response(200, json=metadata_fixture)
        return httpx.Response(404, json={"ok": False, "error": "Not found"})
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )


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

**Assertion patterns to copy** (from `test_database.py`):
- `test_*_returns_200_with_*` — body shape assertions (`/static/css/zeeker.css` link, `class="..."`)
- `test_*_italic_accent_h1` — regex: `re.compile(r"<h1>.*?<em>[^<]+</em>.*?</h1>", re.DOTALL)`
- `test_*_cache_control_header` — assert `max-age=60` AND `stale-while-revalidate=300`
- `test_*_filters_hidden_zeeker_tables` — assert `_zeeker` not in body
- `test_*_renders_breadcrumb` — assert `class="db-crumb"` in body
- `test_*_returns_503_on_upstream_error` — fixture with `httpx.ConnectError("simulated upstream failure")`

---

### `tests/test_routes_search.py` (new — integration test)

**Analog:** `tests/test_routes_table.py` (Phase 5 integration test — multi-fixture handler factory)

**Mock factory pattern** (`test_routes_table.py:54-86`):
```python
def _mock_factory(fixtures, *, raise_on=None):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if raise_on and raise_on in path:
            raise httpx.ConnectError("simulated upstream failure")
        # Match `/sglawwatch/headlines.json?_search=...`
        if path.endswith(".json"):
            params = dict(request.url.params)
            return httpx.Response(200, json=fixtures.get(path, {"rows": []}))
        return httpx.Response(404, json={"ok": False})
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )
```

**Phase 6 specifics** — pre-set `app.state.searchable_tables` directly in the test fixture (no real lifespan invocation):
```python
@pytest.fixture
async def client_search():
    app.state.searchable_tables = {"sglawwatch": ["headlines"], "Zeeker-Judgements": ["judgments"]}
    app.state.http = _mock_factory(...)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac
    finally:
        await app.state.http.aclose()
```

**Critical tests** (RESEARCH §Pitfall 2): one fan-out failure must NOT empty results — `raise_on="/Zeeker-Judgements/judgments.json"` with success on `/sglawwatch/headlines.json` produces non-empty `groups` list.

---

### `tests/test_routes_sql.py` (new — POST integration)

**Analog:** `tests/test_routes_table.py` (handler factory) — adapted to POST + 400 response handling.

**POST test pattern** (no codebase analog yet; FastAPI TestClient + form data):
```python
@pytest.mark.asyncio
async def test_sql_post_runs_query(client_sql):
    r = await client_sql.post("/sql/sglawwatch", data={"sql": "SELECT 1"})
    assert r.status_code == 200
    assert "<table" in r.text
    assert "Cache-Control" in r.headers and "no-store" in r.headers["Cache-Control"]


@pytest.mark.asyncio
async def test_sql_post_renders_400_error_inline(client_sql_with_400):
    """RESEARCH Pitfall 1 — datasette returns 400 with populated `error` field;
    handler must render it inline, not 503."""
    r = await client_sql_with_400.post("/sql/sglawwatch", data={"sql": "SELECT * FROM nope"})
    assert r.status_code == 200
    assert "no such table" in r.text  # body.error rendered
```

Mock handler returns `httpx.Response(400, json={"ok": False, "error": "no such table: nope", "rows": [], "columns": []})` to exercise Pattern 4.

---

### `tests/test_datasette_client_phase06.py` (new — unit test)

**Analog:** `tests/test_datasette_client_table_row.py` (pure unit tests for `fetch_table`/`fetch_row` — no FastAPI app)

**Mock helper pattern** (`test_datasette_client_table_row.py:10-15`):
```python
def _mock(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(handler),
    )
```

**Per-helper test pattern** (`test_datasette_client_table_row.py:18-104`):
```python
@pytest.mark.asyncio
async def test_search_table_passes_q_and_size():
    captured = {}
    def h(req: httpx.Request) -> httpx.Response:
        captured["params"] = dict(req.url.params)
        return httpx.Response(200, json={"rows": [], "columns": []})
    async with _mock(h) as c:
        await search_table(c, "db", "tbl", "DBS", 10)
    assert captured["params"]["_search"] == "DBS"
    assert captured["params"]["_size"] == "10"
    assert captured["params"]["_shape"] == "objects"


@pytest.mark.asyncio
async def test_execute_sql_400_returns_friendly_error():
    """RESEARCH §Pitfall 1 — body.error populated on 400."""
    async with _mock(lambda r: httpx.Response(
        400, json={"ok": False, "error": "no such table", "rows": []}
    )) as c:
        body, error = await execute_sql(c, "db", "SELECT * FROM nope")
    assert body is None
    assert "no such table" in error
```

**Coverage targets:** every new helper (`discover_searchable_tables`, `search_table`, `execute_sql`) gets the equivalent of `test_fetch_table_*` — happy path, 404, 500, allowlist enforcement, `_shape=objects` always present.

---

### `tests/test_changelog.py` (new — unit test)

**Analog:** none (pure file-I/O unit test). Pattern follows `test_filters.py` for module-level Python tests:
```python
import pytest
from pathlib import Path
from zeeker_frontend.changelog import load_changelog

def test_load_changelog_returns_list_of_dicts(tmp_path, monkeypatch):
    yaml_file = tmp_path / "changelog.yaml"
    yaml_file.write_text("recent_updates:\n  - date: '2025-06-09'\n    type: feature\n    title: Launch\n    description: hi\n")
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    items = load_changelog()
    assert len(items) == 1
    assert items[0]["date"] == "2025-06-09"

def test_load_changelog_returns_empty_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    assert load_changelog() == []

def test_load_changelog_returns_empty_on_invalid_yaml(tmp_path, monkeypatch):
    (tmp_path / "changelog.yaml").write_text("!!!not valid yaml: [")
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    assert load_changelog() == []
```

---

### `tests/fixtures/*.json` (new — 4 files)

**Analog:** existing `tests/fixtures/sglawwatch.json` (database response shape), `headlines_table.json` (table response shape with `rows`, `columns`, `primary_keys`, `filtered_table_rows_count`)

**New fixtures** (capture from live Datasette per RESEARCH §Architecture Patterns):
- `searchable_databases.json` — output of `discover_searchable_tables` (just `{db: [tables]}`); pre-set on `app.state` in tests
- `headlines_search_results.json` — `/sglawwatch/headlines.json?_search=DBS&_size=10&_shape=objects` shape (rows + filtered_table_rows_count + primary_keys)
- `metadata_with_canned_queries.json` — variant of `metadata.json` with `databases.{db}.queries.{name}` populated for `/sql/{db}` canned-query tests
- `sql_error_400.json` — `/sglawwatch.json?sql=BROKEN` 400 response: `{"ok": false, "error": "no such table: nope", "rows": [], "columns": [], "truncated": false}`

Capture pattern: `curl -s "http://localhost/sglawwatch.json?...&_shape=objects" > tests/fixtures/X.json`. Same approach Phase 4-5 used for the existing fixtures.

---

### `scripts/verify_phase_06.sh` (new)

**Analog:** `scripts/verify_phase_05.sh` (RESEARCH §Pitfall 11 — author NEW script, do NOT edit Phase 5's destructively)

**Header + delegation pattern** (`verify_phase_05.sh:1-38`):
```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BASE_URL="${BASE_URL:-http://localhost}"
ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0
echo "== Phase 6 verifier (BASE_URL=$BASE_URL) =="

# A. Phase-4 invariants (delegate)
echo
echo "A. Phase-4 invariants (delegating to verify_phase_04.sh)"
if [ "$BASE_URL" = "http://localhost" ]; then
  if bash scripts/verify_phase_04.sh; then ok "..."; else fail "..."; fi
fi
```

**Boundary-flip pattern** (`verify_phase_05.sh:294-302` Phase-5 boundary asserts — flip from "expect 404" to "expect 200 + body shape"):
```bash
# OLD (verify_phase_05.sh:295-301):
for P in developers status sources about how-to-use llms.txt; do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/$P")
  if [ "$CODE" = "404" ]; then ok "/$P → 404"; else fail "..."; fi
done

# NEW (verify_phase_06.sh):
for P in developers status sources about how-to-use; do
  BODY=$(curl -fsS "$BASE_URL/$P" 2>/dev/null || echo "__CURL_FAIL__")
  if echo "$BODY" | grep -q '__CURL_FAIL__'; then fail "/$P unreachable"; continue; fi
  echo "$BODY" | grep -qE '<h1>[^<]*<em[^>]*>[^<]+</em>' && ok "/$P 200 + italic-accent H1" || fail "/$P missing italic H1"
  echo "$BODY" | grep -q '/static/css/zeeker.css' && ok "/$P references /static/css/zeeker.css" || fail "/$P missing frontend CSS link"
done

# /llms.txt — text/plain
CT=$(curl -fsS -D - -o /dev/null "$BASE_URL/llms.txt" 2>/dev/null | grep -i '^content-type:' | tr -d '\r')
echo "$CT" | grep -qi 'text/plain' && ok "/llms.txt Content-Type: text/plain" || fail "/llms.txt wrong Content-Type"

# /robots.txt
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/robots.txt")
[ "$CODE" = "200" ] && ok "/robots.txt → 200" || fail "/robots.txt → $CODE"

# /-/search and /-/sql still reach datasette (D-01 — frontend NEVER under /-/)
SEARCH_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/-/search")
case "$SEARCH_CODE" in 200|404) ok "/-/search → $SEARCH_CODE (datasette)" ;;
  *) fail "/-/search returned $SEARCH_CODE" ;; esac
```

**API parity wrap** (`verify_phase_05.sh:320-330`):
```bash
echo "O. API byte-parity vs .planning/baselines/phase-03-pre/"
export ZEEKER_BASELINE_DIR="$ROOT/.planning/baselines/phase-03-pre"
bash scripts/verify_api_parity.sh && ok "verify_api_parity.sh" || fail "..."
```

---

## Shared Patterns

### Authentication / Authorization
**Source:** none — public read-only API throughout. No middleware, no guards.
**Apply to:** N/A. Phase 6 does NOT introduce authentication; SQL execution is read-only at the Datasette engine level (D-08).

---

### Cache-Control headers (D-14 — load-bearing)
**Source:** `routes_database.py:71`, `routes_table.py:129`, `routes_row.py:113`, `routes_home.py:57`
**Apply to:** Every Phase-6 GET handler. POST `/sql/{db}` uses `no-store` instead.
```python
response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
return response
```
**Anti-pattern:** forgetting the header. Verifier asserts both `max-age=60` and `stale-while-revalidate=300` on every GET (`verify_phase_05.sh:60-64`).

---

### Error handling (503 on upstream, 404 on missing)
**Source:** `routes_database.py:21-27`, `routes_table.py:36-42`, `routes_home.py:35-38`
**Apply to:** All Phase-6 route handlers that call `datasette_client.*` helpers.
```python
try:
    payload = await fetch_database(client, db)
except httpx.HTTPError:
    raise HTTPException(status_code=503, detail="Data API unavailable")

if payload is None:
    raise HTTPException(status_code=404, detail="Database not found")
```
**Anti-pattern:** swallowing httpx errors and returning empty results, or using `raise_for_status()` before checking 400-with-body (RESEARCH Pitfall 1) on `/sql/{db}`.

---

### Hidden-table filter (D-15 — load-bearing predicate)
**Source:** `routes_database.py:33-36`, `datasette_client.py` (referenced in `discover_searchable_tables` per RESEARCH §Pattern 2)
**Apply to:** Every page that lists tables — `/sources`, `/developers`, `/llms.txt`, `/sql/{db}` canned-queries.
```python
visible_tables = [
    t for t in payload.get("tables", [])
    if not t.get("hidden") and not t.get("name", "").startswith("_zeeker")
]
```
**Two predicates required (RESEARCH Pitfall 4):** the `hidden: true` flag covers FTS internals (`*_fts`, `*_fts_data`, etc.) but NOT `_zeeker_*` platform tables (those have `hidden: false` in some overlays). Both predicates are mandatory.

---

### Querystring allowlist (Pitfall 7 — close SSRF surface)
**Source:** `datasette_client.py:68-94` (`_TABLE_ALLOWED_PARAMS`)
**Apply to:** `routes_sql.py` POST handler — build `ds_params` explicitly from `sql` + detected `:param` names; DROP everything else in `request.form()`.
```python
ds_params = {"sql": sql, "_shape": "objects"}
for name in _detect_params(sql):
    if name in param_values:
        ds_params[f"_param_{name}"] = param_values[name]
# Anything else in request.form() is silently dropped.
```

---

### Italic-accent H1 (D-16 — every aux page)
**Source:** `database.html:21-30` (last-word-italic split logic) — use the simpler hard-coded version since aux H1 copy is locked by UI-SPEC.
**Apply to:** Every aux page template.
```jinja
<h1>About <em>Zeeker</em></h1>
<h1>Developer <em>portal</em></h1>
<h1>Recent <em>updates</em></h1>
<h1>Data <em>sources</em></h1>
<h1>How to use <em>this site</em></h1>
<h1>Search across <em>everything</em></h1>     {# /search State A #}
<h1>Run <em>SQL</em></h1>                        {# /sql landing #}
```

Verifier regex: `re.compile(r"<h1>.*?<em>[^<]+</em>.*?</h1>", re.DOTALL)` (`test_database.py:103`).

---

### Frontend CSS reference (REQ-eliminate-template-drift)
**Source:** `base.html:7` — `<link rel="stylesheet" href="/static/css/zeeker.css">`
**Apply to:** Every aux page (inherited via `{% extends "base.html" %}` — no per-page CSS link needed).
**Anti-pattern:** referencing M1 path `zeeker-base.css`. Verifier explicitly fails: `if echo "$BODY" | grep -q 'zeeker-base.css'; then fail "LEAKS M1 path"`.

---

### Body-class scoping for Phase-6 CSS
**Source:** UI-SPEC §Page Surfaces — every aux handler passes `page_class="page-{slug}"`; `base.html` binds it via one-line edit `<body class="{{ page_class or '' }}">`.
**Apply to:** Every Phase-6 handler context dict + the `base.html` `<body>` tag.
```python
context = {..., "page_class": "page-developers"}
```
```jinja
{# base.html — single edit at line 10 #}
<body class="{{ page_class or '' }}">
```
**Why:** scopes Phase-6 CSS subsections (`.page-developers .api-table`) without leaking into Phase 4-5 surfaces.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `changelog.py` | utility | file-I/O | No prior YAML loader in frontend; `datasette_client.py` cache helpers only partially match (in-memory dict, no file). Pattern is novel — RESEARCH §Pattern 3 is the source of truth. |
| `static/js/aux.js` (Discretion) | JS utility | event-driven | No prior JS in frontend. The 8-line snippet is self-documenting; no analog needed. |
| `tests/test_changelog.py` | test | file-I/O | Pure module unit test; closest is `test_filters.py` (Python module test) but that doesn't read files. Pattern: `tmp_path` fixture + `monkeypatch.setattr("...changelog._DATA_DIR", tmp_path)`. |

---

## Metadata

**Analog search scope:**
- `packages/zeeker-frontend/src/zeeker_frontend/` — all Python modules
- `packages/zeeker-frontend/src/zeeker_frontend/templates/` — base + page + partials
- `packages/zeeker-frontend/tests/` — conftest + integration + unit tests
- `plugins/` — M1 Datasette plugin reference (data shape only — port, do not copy idiom)
- `templates/pages/` — M1 templates (port section ordering + content)
- `static/css/zeeker-base.css` — M1 CSS (harvest subsections per UI-SPEC §CSS Harvest)
- `scripts/verify_phase_05.sh` — verifier shape

**Files scanned:** 24 source files, 9 templates, 7 test files, 1 verifier script, M1 reference: 5 plugins + 6 templates + 1 CSS file + 1 strings.yaml

**Pattern extraction date:** 2026-04-25

---

*Phase: 06-port-auxiliary-pages*
*Pattern map: complete*

# Phase 5: Port table browse + row view — Research

**Researched:** 2026-04-25
**Domain:** FastAPI/Jinja port of `/{db}/{table}` and `/{db}/{table}/{pk}` driven by Datasette JSON API; civic-broadsheet editorial UI per locked design contract
**Confidence:** HIGH on Datasette JSON shapes (verified from local source + captured baselines), HIGH on carry-forward patterns (Phase 4 SUMMARY chain is fresh), MEDIUM on M1 CSS harvest (only feed cards exist in M1 — facets, article, aside, dateline, coda, data-table, pagination must be authored fresh from sketch references).

## Summary

Phase 5 adds two FastAPI route modules (`routes_table.py`, `routes_row.py`) and two Jinja templates (`table.html`, `row.html`) that consume two Datasette JSON endpoints — `/{db}/{table}.json` and `/{db}/{table}/{pk}.json` — and render them under the M2 editorial shell already established in Phase 4. The Datasette response shapes are fully verified against the running 0.65.2 source tree under `.venv/` and against captured baselines under `.planning/baselines/phase-03-pre/`. There is **no Datasette HTML in the loop**: the frontend talks JSON-only and renders its own HTML via Jinja.

Two non-obvious load-bearing facts shape every plan downstream. (1) Datasette's table JSON returns `rows` as **list-of-lists** keyed against a separate `columns` array — there is no row-as-dict shape unless you request `?_shape=objects`. The frontend should request `_shape=objects` so Jinja templates can index by column name without a zip. (2) Datasette 0.65 has **no `_search_highlight` field** — the FTS hit is a row-set filter only, with no per-row highlight data exposed to the JSON consumer. UI-SPEC's `<mark>` highlight has to be done client-side or skipped; this contradicts a CONTEXT discretion line and needs to be flagged to the planner as a downgrade.

The locked CONTEXT decisions (D-01 generic template, D-02 metadata.json display hints, D-03 separate table/row modes, D-04 tabular fallback, D-05 export = direct anchor, D-06 no inline SQL editor) are all consistent with the available data. The display-hint schema in CONTEXT §Specific Ideas works; the only adjustment is that the existing `metadata.json` `databases.*.tables` schema is documented in M1 CLAUDE conventions and the proposed `display.{table_mode,row_mode,columns}` namespace nests inside cleanly without conflict.

**Primary recommendation:** Five plans, sequenced — (1) extend `datasette_client.py` with `fetch_table` + `fetch_row` + URL helper module; (2) author `routes_table.py` + `table.html` + tests; (3) author `routes_row.py` + `row.html` + tests; (4) append the `TABLE BROWSE + ROW VIEW — phase 05` CSS section to `zeeker.css`; (5) author `verify_phase_05.sh` + add display hints to `metadata.json` for sglawwatch.headlines, sglawwatch.about_singapore_law, Zeeker-Judgements.judgments. CSS plan (4) can run parallel to plans (2)/(3) by file (different file). The remainder are sequential because both routers append to `main.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pagination state (cursor next_url) | API / Backend (datasette) | Frontend Server (preserve querystring) | Datasette owns pagination state; frontend forwards opaque cursor token via `?_next=` in next-page URL |
| Facet computation | API / Backend (datasette) | Frontend Server (rendering only) | Datasette computes counts; frontend renders the `facet_results` object |
| FTS query execution | API / Backend (datasette) | Frontend Server (`?_search=` forwarding) | Datasette runs SQLite FTS5; frontend just passes the `_search` querystring through |
| Sort | API / Backend | Frontend Server (clickable headers build URL) | Datasette honors `?_sort=` / `?_sort_desc=`; frontend mints the URLs |
| Export rendering | CDN / Edge (Caddy) | — | Caddy `@datasette` matcher catches `.csv`/`.json` suffix; never enters frontend (D-05 locked) |
| Row layout dispatch (table_mode/row_mode) | Frontend Server (Jinja) | API / Backend (metadata source) | Frontend reads `display.*` from `/-/metadata.json` (cached) and branches Jinja |
| Querystring munging (toggle facet, change sort, change size) | Frontend Server (helpers in `urls.py`) | — | Pure URL composition — datasette helpers are used inside its own templates only; frontend ports the same logic in Python |
| Hidden-table/`_zeeker_` filter | Frontend Server | — | Same single-predicate filter Phase 4 established (`hidden=True OR name.startswith("_zeeker")`) — applied to row-level operations too |
| HTML rendering | Frontend Server (Jinja2Templates) | — | All HTML in zeeker-frontend; zero Datasette template surface (REQ-eliminate-template-drift) |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-frontend-route-set | Frontend serves `/{db}/{table}` + `/{db}/{table}/{pk}` | Two new APIRouters + two Jinja templates; route registration order documented (§Registration Order) |
| REQ-frontend-data-via-http | Frontend reads exclusively via HTTP | `fetch_table` + `fetch_row` extend the existing `datasette_client.py` httpx-only pattern |
| REQ-api-byte-parity | `.json`/`.csv` URLs return identical bytes | D-05 routes exports through Caddy; suffix-routing already verified Phase 3; no change in Phase 5 |
| REQ-eliminate-template-drift | Single HTML codebase, no per-table overrides | D-01 locks one `table.html` + one `row.html`; mode dispatch via `display.*` in metadata, not template proliferation |
| PRD R1 | Facet edge cases (array, m2m) | Verified: array facets need separate `?_facet_array=col` URL param + `facet_results[col].type=='array'` shape; m2m has no first-class datasette support — graceful fallback documented |

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** One generic `table.html` template drives every table. **No per-table Jinja override files** (no `_table-{db}-{table}.html` proliferation).
- **D-02:** Per-table rendering is controlled by `metadata.databases.{db}.tables.{table}.display` hints inside the existing `metadata.json`. No new config files.
- **D-03:** Separate `display.table_mode` (e.g. `feed`, `tabular`, `longform-list`) and `display.row_mode` (e.g. `article`, `judgment`, `longform`, `tabular`).
- **D-04:** When neither mode is set, fall back to **tabular** on both pages (dense `<table>` + key-value `<dl>`).
- **D-05:** Export links go **direct to datasette via Caddy suffix routing** — `<a href="/{db}/{table}.csv?{qs}">`. Frontend's only job is constructing the link.
- **D-06:** **Inline SQL editor / per-column filter inputs DEFERRED to Phase 6.** Phase 5 ships facets + pagination + sort + FTS only.

### Claude's Discretion (pre-decided defaults from CONTEXT § Claude's Discretion)
- **Facets:** collapsible-accordion-style sticky sidebar; chip pills above for applied facets.
- **Pagination:** cursor-based via `next_url`; 25/50/100 page-size selector; no numbered pages.
- **FTS:** hero search input → `?_search=`; **CONTEXT proposes `<mark>` highlight from `_search_highlight`** — see §Datasette JSON Contract for the contradiction (no such field exists in 0.65.2). Recommend client-side regex highlight on the JS-free path or explicit downgrade.
- **Sort:** column-header click cycles asc → desc → clear.
- **Cache-Control:** `public, max-age=60, stale-while-revalidate=300` (Phase-4 carry-forward).

### Deferred Ideas (OUT OF SCOPE)
- Inline SQL editor / `/-/sql`-like → Phase 6.
- Global `/-/search` cross-database → Phase 6.
- Permalink URL polish (replacing cursor tokens with `?page=N`) → defer unless visibly ugly.
- Numbered pagination → deferred (datasette doesn't expose total-count cheaply).
- Facet array-column / m2m exhaustive UX → planner notes as "graceful fallback acceptable" unless surfaces in sglawwatch / Zeeker-Judgements.
- Permalink-stable cursor UX, prev/next-row navigation in row detail.
- Production deploy (still deferred from Phase 4).

## Project Constraints (from CLAUDE.md)

| Directive | Source | How it constrains Phase 5 |
|-----------|--------|--------------------------|
| No hardcoded database references | CLAUDE §Architecture | Templates branch on `display.*` hints, not on `db == "sglawwatch"` checks |
| `_zeeker_*` metadata tables hidden | CLAUDE §Notes | Same single-predicate filter Phase 4 established — applies to row routes too if a `_zeeker_*` table is requested by URL |
| Three-pass merge (base + S3 overlay) | CLAUDE §Architecture | Display hints land in **base `metadata.json`** for canonical project tables; per-database overlays can extend with their own hints (no Phase-5 overlay work needed since hints are in the base file) |
| Self-hosted fonts only | CLAUDE §Architecture | Phase-4 already moved Inter / Fraunces / JetBrains Mono into `static/fonts/`; Phase 5 doesn't add fonts |
| `uv` for dependency management | CLAUDE §Dependencies | If any new deps added (don't expect any), use `uv add` |
| CORS enabled on API endpoints | CLAUDE §Notes | API endpoints (the `.json` URLs) are still served by datasette through Caddy; CORS preserved unchanged |
| `pytest` for tests | CLAUDE §Development | New tests under `packages/zeeker-frontend/tests/` use existing pytest-asyncio + pytest-httpx + ASGITransport pattern |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | already pinned (Phase 4) | Route module via APIRouter, HTMLResponse, HTTPException | Carry-forward — same pattern as `routes_home.py` / `routes_database.py` `[VERIFIED: routes_database.py source]` |
| Jinja2 (via `fastapi.templating.Jinja2Templates`) | already pinned | HTML rendering with autoescape | Carry-forward — `app.state.templates` exists; just add new template files `[VERIFIED: main.py:82]` |
| httpx.AsyncClient | already pinned | JSON calls to datasette | Carry-forward — `app.state.http` exists with timeout 10s, max 20 connections `[VERIFIED: main.py:43-47]` |

### Supporting (already in repo, no new deps required)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `urllib.parse` (stdlib) | — | Querystring parsing + encoding for `urls.py` helper module | Implementing `path_with_replaced_args` / `path_with_added_args` / `path_with_removed_args` ports `[VERIFIED: datasette/utils/__init__.py:268-331]` |
| pytest-asyncio + pytest-httpx | already in dev | MockTransport tests for the new routes | Same pattern as `test_database.py` — works without docker `[VERIFIED: tests/conftest.py]` |
| FastAPI's `httpx.ASGITransport` | already in dev | Integration test driving the FastAPI app via httpx | Same pattern as `test_database.py:38-47` |

### Alternatives Considered (and rejected per CONTEXT)
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One `table.html` | Per-table `_table-{db}-{table}.html` (M1 pattern) | **Rejected by D-01** — re-introduces template drift the migration is meant to eliminate |
| `display.*` in metadata.json | Frontend-side `display.json` next to templates | **Rejected by D-02** — divorces display from per-DB metadata; new file; no S3-overlay inheritance |
| Frontend proxies CSV/JSON exports | Build a streaming CSV proxy in FastAPI | **Rejected by D-05** — extra hop, parity drift risk; Caddy already handles it |
| Search ranking via `datasette-search-all` | Phase 5 implements cross-DB | **Out of scope** — `/-/search` is Phase 6 |

**No new packages.** Every dependency is already pinned. Phase-5 is pure Python + Jinja + CSS authoring.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────┐
   Browser GET ───► │  Caddy :80   │
                    │              │
                    │  @datasette  │── path *.json *.csv *.db /-/* ──► [datasette:8001]
                    │  (suffix)    │
                    │              │
                    │  default ────│──► [frontend:8000]
                    └──────────────┘
                            │
                            ▼  /{db}/{table}  or  /{db}/{table}/{pk}
                    ┌──────────────────────┐
                    │  FastAPI app         │
                    │  app.state.http      │
                    │  app.state.templates │
                    └──────────────────────┘
                            │
            ┌───────────────┴────────────────┐
            ▼                                ▼
    routes_table.py                    routes_row.py
            │                                │
            │  fetch_table()                 │  fetch_row()
            │  + fetch_site_metadata()       │  + fetch_site_metadata()
            ▼                                ▼
    ┌─────────────────────┐         ┌──────────────────────┐
    │ datasette_client.py │         │  same client module  │
    │  GET /{db}/{table}  │         │  GET /{db}/{table}/  │
    │     .json?_shape=   │         │       {pk}.json?     │
    │     objects&_size&  │         │       _shape=objects │
    │     _facet&_search& │         └──────────────────────┘
    │     _sort           │                    │
    └─────────────────────┘                    │
            │                                  │
            │ HTTP (internal docker bridge)    │
            ▼                                  ▼
            ┌──────────────────────────────────┐
            │  zeeker-datasette:8001           │
            │  (read-only SQLite, FTS5)        │
            └──────────────────────────────────┘

Mode dispatch (per template, post-fetch):

    table.html
      ├─ display.table_mode == "feed"          → feed-card layout (sketch 004-A)
      ├─ display.table_mode == "longform-list" → simplified feed (no excerpt, no pill)
      └─ default ("tabular" | None)            → <table> grid (sketch 002-B baseline)

    row.html
      ├─ display.row_mode == "article"  → magazine layout + sticky aside (sketch 003-A)
      ├─ display.row_mode == "judgment" → editorial broadsheet (sketch 003-B)
      ├─ display.row_mode == "longform" → reading column only, no aside, no drop cap
      └─ default ("tabular" | None)     → key-value <dl> + aside

Export anchors construct URL only — Caddy intercepts before frontend sees them:

    <a href="/{db}/{table}.csv?{qs}">CSV ↗</a>  → Caddy @datasette → datasette
    <a href="/{db}/{table}.json?{qs}">JSON ↗</a> → Caddy @datasette → datasette
```

### Recommended Project Structure

```
packages/zeeker-frontend/src/zeeker_frontend/
├── main.py                                    # MODIFIED — register 2 new routers
├── datasette_client.py                        # MODIFIED — add fetch_table, fetch_row
├── urls.py                                    # NEW — querystring helpers (port from datasette/utils)
├── routes_home.py                             # untouched
├── routes_database.py                         # untouched
├── routes_table.py                            # NEW — GET /{db}/{table}
├── routes_row.py                              # NEW — GET /{db}/{table}/{pk}
├── filters.py                                 # untouched
├── templates/
│   ├── base.html                              # untouched
│   ├── index.html                             # untouched
│   ├── database.html                          # untouched
│   ├── table.html                             # NEW — generic table page
│   ├── row.html                               # NEW — generic row page
│   └── _partials/
│       ├── feed_card.html                     # NEW — extracted feed-card render (parity with M1 partial)
│       ├── facet_sidebar.html                 # NEW — sticky facets sidebar
│       ├── pagination.html                    # NEW — prev/next + size selector
│       └── applied_facets.html                # NEW — applied-facet chips above content
└── static/css/zeeker.css                      # MODIFIED — append TABLE BROWSE + ROW VIEW section
```

### Pattern 1: Two-call route handler with safe metadata merge

```python
# Source: extending the established routes_database.py pattern
# [VERIFIED: routes_database.py:15-72]

@router.get("/{db}/{table}", response_class=HTMLResponse)
async def table_page(request: Request, db: str, table: str):
    client: httpx.AsyncClient = request.app.state.http

    # Apply hidden filter early — request to a hidden table 404s
    if table.startswith("_zeeker"):
        raise HTTPException(status_code=404, detail="Table not found")

    # Forward all browser-controlled query params to datasette
    qs = dict(request.query_params)

    try:
        payload = await fetch_table(client, db, table, qs)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Data API unavailable")

    if payload is None:
        raise HTTPException(status_code=404, detail="Table not found")

    site_metadata = await fetch_site_metadata(client)
    table_meta = (
        (site_metadata.get("databases") or {})
        .get(db, {})
        .get("tables", {})
        .get(table, {})
    )

    # display hints — drop straight in
    display = table_meta.get("display") or {}
    table_mode = display.get("table_mode") or "tabular"

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="table.html",
        context={
            "database": db,
            "table": table,
            "rows": payload["rows"],            # already objects via _shape=objects
            "columns": payload["columns"],
            "primary_keys": payload["primary_keys"],
            "facet_results": payload.get("facet_results") or {},
            "suggested_facets": payload.get("suggested_facets") or [],
            "filtered_table_rows_count": payload.get("filtered_table_rows_count"),
            "next_url": payload.get("next_url"),
            "next": payload.get("next"),
            "human_description_en": payload.get("human_description_en"),
            "request_qs": request.url.query,    # original querystring for export-link construction
            "table_mode": table_mode,
            "display": display,
            "table_meta": table_meta,
            "metadata": _merge_metadata(site_metadata, db, table, payload),
            "breadcrumbs": [
                {"href": f"/{db}", "label": db_title(site_metadata, db)},
                {"label": table_meta.get("title") or table},
            ],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

### Pattern 2: Querystring helpers (port from datasette source)

```python
# packages/zeeker-frontend/src/zeeker_frontend/urls.py
# Direct ports of datasette/utils/__init__.py:268-331 — public API.
# [VERIFIED: datasette/utils/__init__.py:268-331]

from urllib.parse import parse_qsl, urlencode

def path_with_added_args(path: str, query_string: str, args) -> str:
    """args is a dict (or list of pairs); None values trigger removal."""
    if isinstance(args, dict):
        args = list(args.items())
    args_to_remove = {k for k, v in args if v is None}
    current = [(k, v) for k, v in parse_qsl(query_string) if k not in args_to_remove]
    current.extend([(k, v) for k, v in args if v is not None])
    qs = urlencode(current)
    return f"{path}?{qs}" if qs else path


def path_with_replaced_args(path: str, query_string: str, args) -> str:
    """Replace specific keys, preserving everything else."""
    if isinstance(args, dict):
        args = list(args.items())
    keys = {k for k, _ in args}
    current = [(k, v) for k, v in parse_qsl(query_string) if k not in keys]
    current.extend([(k, v) for k, v in args if v is not None])
    qs = urlencode(current)
    return f"{path}?{qs}" if qs else path


def path_with_removed_args(path: str, query_string: str, keys: set[str]) -> str:
    current = [(k, v) for k, v in parse_qsl(query_string) if k not in keys]
    qs = urlencode(current)
    return f"{path}?{qs}" if qs else path


def export_url(db: str, table: str, ext: str, query_string: str) -> str:
    """Construct CSV/JSON export URL — Caddy intercepts via @datasette."""
    base = f"/{db}/{table}.{ext}"
    return f"{base}?{query_string}" if query_string else base
```

These are exposed as Jinja globals on `templates.env.globals`, mirroring how datasette exposes the same helpers in `table.py:763-766` `[VERIFIED]`.

### Pattern 3: Mode dispatch in Jinja (no Python branching)

```jinja
{# table.html — mode dispatch via include #}
{% if table_mode == "feed" %}
  {% include "_partials/table_modes/feed.html" %}
{% elif table_mode == "longform-list" %}
  {% include "_partials/table_modes/longform_list.html" %}
{% else %}
  {# default: tabular #}
  {% include "_partials/table_modes/tabular.html" %}
{% endif %}
```

Same pattern for `row.html` (article / judgment / longform / tabular). Keeps the dispatch declarative; each mode partial owns its own DOM tree.

### Anti-Patterns to Avoid
- **Don't re-introduce per-table Jinja overrides.** D-01 locked. If `display.table_mode` isn't expressive enough for a future table, add a new mode value, never a per-table partial.
- **Don't request `_shape=arrays` (the default).** It returns `rows: list[list]`; templates would need `zip(columns, row)` everywhere. **Always request `?_shape=objects`** so each row is a dict keyed by column name. `[VERIFIED: datasette docs `_shape=objects` returns row-as-dict]`
- **Don't construct querystrings with manual string concat.** Use the `urls.py` helpers; URL encoding around facet values with spaces / `&` / `+` will silently break otherwise.
- **Don't render `<mark>` from a `_search_highlight` field.** That field doesn't exist in datasette 0.65.2 JSON. Either client-side highlight via JS, or skip highlight entirely (CONTEXT discretion downgrade).
- **Don't proxy CSV/JSON through the frontend.** D-05 locked; Caddy `@datasette` matcher catches the suffix before the request reaches FastAPI. Verifier asserts this.
- **Don't bypass the hidden-table filter on row routes.** `_zeeker_*` tables shouldn't be browsable by URL either; 404 them at handler entry.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination state | Page-counted paginator | Datasette's `next_url` / `next` cursor token | Datasette uses opaque continuation tokens; total-count is expensive. Just forward `next_url` as the "Next →" anchor `[VERIFIED: views/table.py:803-804]` |
| Facet computation | Custom SQL per facet column | `?_facet=col` and the `facet_results[col].results` shape | Datasette's facet engine handles type detection (column / array / date), null suppression, count limits, and toggle-URL generation `[VERIFIED: facets.py:67-568]` |
| FTS query | Re-implement search ranking | `?_search=term` (passes straight to datasette's FTS5 SQL) | Datasette already integrates SQLite FTS5; ranking is handled `[VERIFIED: views/table.py:712]` |
| URL querystring munging | Hand-rolled string concat | `urls.py` ports of `path_with_*_args` | Datasette's helpers handle URL-encoding edge cases (spaces, `+`, repeated keys, `None` deletion); reimplementing risks subtle bugs `[VERIFIED: utils/__init__.py:268-331]` |
| Compound primary key URL encoding | Custom URL encoder | Datasette's `tilde_encode` / comma-joined PK pattern | Compound PKs use comma-joined tilde-encoded segments; matches what datasette emits in `next_url` `[VERIFIED: utils/__init__.py:115-117, 1173-1186]` |
| CSV / JSON export streaming | Build streaming proxy | Direct `<a href>` to `.csv` / `.json` (Caddy intercepts) | D-05 + Phase 3 routing already handle this; zero frontend code |
| Cursor pagination across sort orders | Custom token format | Trust `next_url` from datasette | Datasette already encodes the sort column + last-value-seen into the token |
| Long-text truncation in tabular row mode | JS-based "show more" | `<details><summary>` (browser native) | Native HTML, no JS, accessible by default; UI-SPEC §Interaction Contracts already specifies this |

**Key insight:** Phase 5 is **mostly URL composition + JSON shape mapping**. Almost every "hard" sub-problem (search ranking, facet counts, pagination cursors, encoding) is owned by datasette and exposed in JSON. The frontend's job is rendering, not computation.

## Datasette JSON Contract — Verified Reference

### `GET /{db}/{table}.json?{params}` — table endpoint

**Verified against** local `.venv/lib/python3.12/site-packages/datasette/views/table.py:786-808` and captured `.planning/baselines/phase-03-pre/sglawwatch_headlines.json__size_10.json`.

**Top-level keys** (default `_shape=arrays`):
| Key | Type | Notes |
|-----|------|-------|
| `database` | str | DB name |
| `table` | str | Table name |
| `is_view` | bool | True if SQLite view, not a real table |
| `human_description_en` | str | Optional human-readable description |
| `rows` | **list[list]** | **Default shape returns row arrays — NOT row dicts.** Aligned with `columns` array by index. |
| `columns` | list[str] | Column names in same order as row arrays |
| `primary_keys` | list[str] | Empty `[]` when table has no declared PK (uses rowid implicitly) |
| `truncated` | bool | True when datasette truncated the result |
| `filtered_table_rows_count` | int | Count after filters/search applied (NOT total table count) |
| `expanded_columns` / `expandable_columns` | list | Foreign-key expansion metadata (empty when no FKs) |
| `units` | dict | `{column: unit}` (rarely populated) |
| `query` | dict | `{"sql": "...", "params": {...}}` — the resolved SQL |
| `facet_results` | **dict** | Keyed by facet column name; see facet shape below |
| `suggested_facets` | list[dict] | Datasette's auto-suggestions; each has `{name, type?, toggle_url}` |
| `next` | str \| null | Opaque pagination token |
| `next_url` | str \| null | Full URL for next page (preserves all params) |
| `private` | bool | True if behind auth (always false here) |
| `allow_execute_sql` | bool | Always True for our config |
| `source`, `source_url`, `license`, `license_url` | str | Per-table attribution from metadata.json |

**Critical recommendation: request `?_shape=objects`** — datasette accepts this URL param and returns `rows: list[dict]` keyed by column name. Templates become much simpler. `[VERIFIED: datasette docs lists `objects` as a valid _shape value]`

**Facet result shape** (per facet column):
```json
{
  "name": "category",
  "type": "column",                  // also "array" for ArrayFacet, "date" for DateFacet
  "hideable": false,
  "toggle_url": "/path?...",          // URL to remove this facet
  "results": [
    {
      "value": "Straits Times",
      "label": "Straits Times",
      "count": 500,
      "toggle_url": "/path?category=Straits+Times",  // URL to APPLY this filter
      "selected": false               // true when this value is the active filter
    }
  ],
  "truncated": false
}
```

`[VERIFIED: captured baseline sglawwatch_headlines.json:facet_results.category]`

**Suggested-facet shape** (for the "you might want to facet on this" UI affordance):
```json
[
  {"name": "date", "type": "date", "toggle_url": "/path?_facet_date=date"},
  {"name": "imported_on", "toggle_url": "/path?_facet=imported_on"}
]
```

Phase-5 default UX: **render `facet_results` only**; ignore `suggested_facets` for now (would require an "Add facet" CTA — UI-SPEC doesn't include this; defer or surface as Claude's discretion in plan).

**FTS shape:** When `?_search=foo` is present, datasette returns the same row shape, filtered by FTS match against the table's `*_fts` virtual table. **There is NO `_search_highlight` field in 0.65.x JSON.** `[VERIFIED: grep -nE "highlight|_search_highlight" views/table.py returns no matches; facets.py search has no highlight either]`. Implication: UI-SPEC's `<mark>` highlight rule needs a downgrade — either client-side regex over the rendered HTML, or skip highlight in v1 and document as known gap.

**Pagination shape:** `next_url` is a fully-qualified URL (uses datasette's `BASE_URL` setting; in our docker setup that's `http://localhost/...`). Two implications: (a) the path part is what matters — strip the host before using it as an anchor target; (b) `next_url` already preserves `_sort`, `_search`, `_facet`, applied facet filters — frontend just renders it as the "Next →" anchor.

### `GET /{db}/{table}/{pk}.json` — row endpoint

**Verified against** local `.venv/lib/python3.12/site-packages/datasette/views/row.py:80-102`.

**Top-level keys** (default shape):
| Key | Type | Notes |
|-----|------|-------|
| `database` | str | |
| `table` | str | |
| `rows` | list[list] | **Single-element list** with one row-array |
| `columns` | list[str] | |
| `primary_keys` | list[str] | |
| `primary_key_values` | list[str] | The decoded PK value(s) used to fetch this row |
| `units` | dict | |

**Optional fields** (only present if `?_extras=foreign_key_tables`):
| Key | Notes |
|-----|-------|
| `foreign_key_tables` | List of inbound FK relationships with row counts |

**No `facet_results`, no `next_url`, no FTS payload** — row endpoint is single-record.

**Compound primary key encoding:** PKs are tilde-encoded (`%2F` → `~2F`) and joined with commas. Example: a table with PK `(year, slug)` and row `(2026, "hello/world")` would have URL `/db/table/2026,hello~2Fworld`. The frontend doesn't construct these — datasette's `urls.row(db, table, pks)` handles it server-side, BUT we don't have access to that helper in FastAPI. **What we DO have**: when rendering links to row pages from the table page, the rows already include the PK value(s) as cells; we encode using a port of `tilde_encode`. `[VERIFIED: datasette/utils/__init__.py:1173-1186]`

```python
# packages/zeeker-frontend/src/zeeker_frontend/urls.py — additional helper
def tilde_encode(s: str) -> str:
    """Port of datasette tilde_encode — hex-encodes special URL chars with ~."""
    SAFE = set(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._")
    out = []
    for byte in s.encode("utf-8"):
        if byte in SAFE:
            out.append(chr(byte))
        else:
            out.append(f"~{byte:02X}")
    return "".join(out)


def row_url(db: str, table: str, pk_values: list[str]) -> str:
    """Build /{db}/{table}/{pk1},{pk2},... with tilde-encoding."""
    encoded = ",".join(tilde_encode(str(v)) for v in pk_values)
    return f"/{db}/{table}/{encoded}"
```

**Tables with no declared PK** (like `sglawwatch.about_singapore_law` — `primary_keys: []`): datasette uses `rowid` as the synthetic PK. The row column array starts with `rowid` in this case. Our URL helper needs to detect empty `primary_keys` and emit `/{db}/{table}/{rowid_value}`. `[VERIFIED: captured baseline `sglawwatch_about_singapore_law.json` — first column is `rowid`]`

### Facet edge cases (PRD R1)

**Array columns** (e.g., `subject_tags` on judgments — JSON-array string column):
- Datasette uses a separate URL param: `?_facet_array=col` (NOT `?_facet=col`).
- `facet_results[col].type == "array"` distinguishes it from regular column facets.
- Facet result rows have the same shape; each row is a single distinct array element with its count.
- **Phase 5 strategy:** when rendering the facet sidebar, branch on `facet_results[col].type`. For type `array`, the toggle-URL apply pattern is `?col__contains=value` (datasette provides this in `results[i].toggle_url` already — just render it).
- Verifier should NOT block on array-facet behavior; the assertion is "page renders without 500 when an array facet is configured".
- `[VERIFIED: facets.py:290-455]`

**M2M (many-to-many)**:
- **Datasette has no first-class M2M facet support.** M2M would require either a custom SQL view or a join across the link table.
- Suggested approach: **don't auto-suggest** M2M facets in Phase 5. If a future use case needs them, the user can express the join as a SQLite VIEW and facet that view's columns — datasette treats views the same as tables for facet purposes.
- **Phase-5 graceful behavior:** if a query string includes a column that's neither a table column nor a JSON-array column, datasette returns the row-list with no facet result for that key. The frontend renders the page minus that facet — no error, no 500.

**Date columns:**
- Datasette has `?_facet_date=col` for grouping by date. Suggested-facet returns include `type: "date"`.
- Phase 5: render the same way as `_facet=col` — the facet-result shape is identical.

## Querystring Helpers — Specific Functions Needed

These ship in a new module `packages/zeeker-frontend/src/zeeker_frontend/urls.py` and are registered as Jinja globals:

| Helper | Signature | Use case |
|--------|-----------|----------|
| `path_with_added_args` | `(path, qs, args: dict|list[pair]) -> str` | "Apply this facet" — adds `(col, val)` while preserving everything else. Pass `None` value to delete a key. |
| `path_with_replaced_args` | `(path, qs, args: dict) -> str` | "Change page size" — replaces `_size` with new value, preserves `_search`/`_facet`/etc. |
| `path_with_removed_args` | `(path, qs, keys: set[str]) -> str` | "Clear search" / "Clear sort" — drops `_search` (or `_sort`) entirely. |
| `toggle_facet_value` | `(path, qs, col, val) -> str` | Convenience wrapper: if `col=val` already in qs, remove it; else add. |
| `clear_facet_value` | `(path, qs, col, val) -> str` | Always remove `col=val` from qs (used by `×` chip). |
| `set_sort` | `(path, qs, col, direction: "asc"|"desc"|None) -> str` | Maps to `_sort`/`_sort_desc` mutually exclusively; `None` clears both. |
| `export_url` | `(db, table, ext, qs) -> str` | Build `<a href="/{db}/{table}.csv?{qs}">`. Trivial but explicit so Phase-7 grep can find it. |
| `tilde_encode` | `(s: str) -> str` | Port of `datasette.utils.tilde_encode`; used by `row_url`. |
| `row_url` | `(db, table, pk_values: list[str]) -> str` | Build `/{db}/{table}/{pk1},{pk2},...` with tilde encoding. |

All of these are pure functions; tests sit in `tests/test_urls.py`.

## M1 CSS Harvest Plan

The current `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` is **1102 lines** ending at the FOOTER LINK OVERRIDE block. M1's source `static/css/zeeker-base.css` is **4116 lines**. Phase 5 appends a `/* === TABLE BROWSE + ROW VIEW — phase 05 === */` section just before the FOOTER LINK OVERRIDE (which must remain at file tail to win cascade per Phase-4 WARN-05).

### What exists in M1 zeeker-base.css (harvest direct)

| Section | M1 lines | Target classes | Action |
|---------|---------|----------------|--------|
| FEED CARDS | 3864–3984 | `.va-feed`, `.va-empty`, `.va-item-wrap`, `.va-citation`, `.va-item`, `.va-item-head`, `.va-item-title`, `.va-item-excerpt`, `.va-item-foot`, `.source-host`, `+ media @640px` | **Direct copy** — 121 lines |

### What does NOT exist in M1 (must author fresh from sketch references)

| Section | Source of truth | Approx new lines | Notes |
|---------|----------------|-----------------|-------|
| `.feed-layout` (1fr + 240px sidebar grid) | `references/directory-and-feed-lists.md:117-127` | ~10 | Single grid declaration + media query |
| `.facets`, `.facet-block`, `.facet-item`, `.facet-item.active`, `.facet-item .count` | `references/directory-and-feed-lists.md:117-127` | ~30 | Sticky sidebar, petrol rule-top on first block, hover/active states |
| `.filter-chip` (applied-facet pill with `×`) | new (UI-SPEC §Component Inventory) | ~15 | Pill with petrol bg + paper text + 24px touch target on `×` |
| `.pagination` (cursor prev/next + size selector) | new (UI-SPEC §Component Inventory) | ~25 | Inline flex; mono `--text-xs`; current-size as non-link text |
| `.data-table` (tabular-mode `<table>`) | new + grep `static/css/zeeker-base.css:2092-2255` for any `.data-grid`/`.rows-and-columns` patterns to harvest | ~50 | Sortable `<thead>` headers, zebra rows on `--color-bg-alt`, sort arrow text |
| `.article`, `.read`, `.article-body`, `.kicker`, `.byline`, `.coda` (article reading layout) | `references/row-reading-layouts.md:54-69, 130-138` | ~80 | Includes Fraunces opsz 11 body, max-width 62ch, drop-cap pseudo-element |
| `.aside`, `.aside-block` (sticky metadata sidebar) | `references/row-reading-layouts.md:101-111` | ~25 | Petrol rule-top on first block; mono `<dt>` + display `<dd>` |
| `.dateline` (judgment dark strip) | `references/row-reading-layouts.md:115-125` | ~15 | Ink bg + ochre agency text |
| `.tag-chip` (judgment subject_tags row) | new | ~12 | Surface-sunken pill with mono text |

**Total estimated new CSS: ~270 lines + 121 lines harvested = ~390 lines.** Plan 05-04 should target a CSS file at ~1490 lines after the append.

### Harvest path verification commands

```bash
# 1. Confirm feed-cards CSS section in M1 source still exists at expected lines
sed -n '3864,3984p' /Users/houfu/Projects/zeeker-datasette/static/css/zeeker-base.css

# 2. Confirm current zeeker.css ends with FOOTER LINK OVERRIDE preserved
tail -25 /Users/houfu/Projects/zeeker-datasette/packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css

# 3. Confirm no .va-item / .article / .feed-layout classes already exist in zeeker.css (avoid duplicate definitions)
grep -nE "\.va-item|\.feed-layout|\.facets|\.article|\.aside|\.dateline|\.coda|\.data-table|\.filter-chip|\.pagination" \
     /Users/houfu/Projects/zeeker-datasette/packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css
# expected output: empty (none of these are in zeeker.css yet — verified in research session 2026-04-25)
```

### Section delimiter to use (per Phase-4 convention)

```css
/* =========== TABLE BROWSE + ROW VIEW — phase 05 ============ */
```

Insert immediately before the existing `/* ======================================================= HARVESTED FROM M1 zeeker-base.css LINES 4097..4116 Tail footer link override =======================================================*/` block.

## Display-Hint Schema Confirmation

The proposed schema in CONTEXT §Specific Ideas works as-is. Verification:

**Existing `metadata.json` shape** `[VERIFIED: file read in research session 2026-04-25]`:
```json
{
  "title": "data.zeeker.sg",
  "databases": {
    "sg-gov-newsrooms": {
      "title": "...",
      "tables": {
        "mlaw_news": { "title": "...", "description": "...", "columns": {...} }
      }
    },
    "*": { "allow_sql": true, "tables": { "_zeeker_*": {"hidden": true} } }
  }
}
```

**Proposed extension** — adds a `display` key to existing per-table objects:
```json
{
  "databases": {
    "sg-gov-newsrooms": {
      "tables": {
        "mlaw_news": {
          "title": "Ministry of Law News",
          "description": "...",
          "columns": { "id": "...", ... },
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
      }
    }
  }
}
```

**Tables in scope for hint additions** (Phase 5 plan adds these to `metadata.json`):

| DB | Table | `table_mode` | `row_mode` | Columns slot mapping (M1 reference) |
|----|-------|------------|------------|-------------------------------------|
| `sglawwatch` | `headlines` | `feed` | `article` | kicker=`category`, title=`title`, byline=`author`, body=`summary`, date=`date`, source_url=`source_link` `[VERIFIED: baseline columns]` |
| `sglawwatch` | `about_singapore_law` | `longform-list` | `longform` | kicker=`section`, title=`title`, body=(none — content_length often 0), date=`last_scraped`, source_url=`item_url` `[VERIFIED: baseline]` |
| `Zeeker-Judgements` | `judgments` | `tabular` | `judgment` | title=`case_name`, kicker=`court`, citation=`citation`, date=`decision_date`, body=`text` (or `summary`), source_url=`source_url`, secondary_tags=`subject_tags[]` |
| `sg-gov-newsrooms` | `mlaw_news`, `judiciary_news`, `acra_news`, `agc_news`, `ccs_news`, `ipos_news`, `mom_news`, `pdpc_news` | `feed` | `article` | kicker=`category` (or `content_type` for judiciary), title=`title`, body=`summary`, date=`published_date`, source_url=`source_url` `[VERIFIED: M1 partials confirm same slots]` |

**Recommendation to planner:** plan 05-05 (verifier + metadata) adds `display.*` blocks for the **3 explicit cases above** (headlines, about_singapore_law, judgments). The 8 sg-gov-newsrooms `*_news` tables can be added in the same plan but flagged as "lower priority — same `feed`/`article` shape, identical column mappings". Untouched tables fall back to `tabular` (D-04), which is correct.

**Edge-case schema notes** (planner needs to know):
- The existing `databases.*` wildcard entry has its own `tables: { _zeeker_*: { hidden: true } }`. Display hints on the `*` wildcard are **not propagated** by datasette's metadata merge — hints must live on the specific db entry. `[VERIFIED: M1 metadata.json:50-62 shape, plus M1 routes_database.py uses `databases.{db}` not `databases.*` for table-meta lookups]`
- The hint schema is **declarative-only**; the frontend reads it but doesn't validate it. A future plan may add a JSON-schema validation step in CI.

## Common Pitfalls

### Pitfall 1: `_shape=arrays` is the default and templates can't index by column name

**What goes wrong:** First implementation iterates `{% for row in rows %}{{ row[col] }}` — but `row` is a list, not a dict, so `row["title"]` returns nothing.

**Why it happens:** Datasette's default JSON shape is `arrays` for backward compatibility. Verified in `views/table.py:786-808`: rows come from `await db.execute(...)` and are tuples by default.

**How to avoid:** Always pass `?_shape=objects` when calling datasette from the frontend. Then `row["title"]` works.

**Warning sign:** Test rendering produces empty cells in the feed-card excerpt block.

### Pitfall 2: `next_url` is a fully-qualified URL, not a path

**What goes wrong:** `<a href="{{ next_url }}">Next →</a>` renders as `http://localhost/sglawwatch/headlines.json?_size=10&_next=...` — pointing to the JSON endpoint inside the docker network, not the HTML route.

**Why it happens:** Datasette computes `next_url` using its `absolute_url` helper, which uses the request host. In our docker setup, that's `zeeker-datasette:8001` (or `localhost` from inside the container). Also: it points to `.json` because that's what we requested.

**How to avoid:** In `routes_table.py`, post-process `next_url`: extract the querystring only and prepend `/{db}/{table}` (the HTML path). Plan should specify the helper:
```python
def html_next_url(db, table, datasette_next_url):
    parsed = urlparse(datasette_next_url)
    return f"/{db}/{table}?{parsed.query}" if parsed.query else None
```

**Warning sign:** Clicking "Next →" navigates to a JSON page or an unreachable internal hostname.

### Pitfall 3: No `_search_highlight` field exists in datasette 0.65.x

**What goes wrong:** Template references `row.search_highlight` or filters on a `_search_highlight` key that's never present.

**Why it happens:** UI-SPEC §Interaction Contracts mentions `<mark>` highlight from `_search_highlight`; CONTEXT §Claude's Discretion mentions the same. **But this field doesn't exist** — `grep "highlight" /Users/houfu/Projects/zeeker-datasette/.venv/lib/python3.12/site-packages/datasette/views/table.py` returns nothing.

**How to avoid:** Two options for the planner:
1. **Skip highlight in v1** — render the search term in the toolbar chip ("Search: foo ×") and trust the user to scan the filtered rows.
2. **Client-side highlight** — small JS that wraps `<mark>` around exact-match strings in rendered cells. Adds JS dependency we've otherwise avoided.

Recommend (1); defer (2) as a Phase-6 follow-up if user feedback flags scanning fatigue.

**Warning sign:** Tests for `<mark>` rendering all fail.

### Pitfall 4: Tables with `primary_keys: []` (no declared PK)

**What goes wrong:** Building a row link from `row[primary_keys[0]]` raises `IndexError` for tables like `sglawwatch.about_singapore_law` where datasette returns `primary_keys: []`.

**Why it happens:** Datasette uses `rowid` as a synthetic PK in this case; it's the first column in `columns` and the row array.

**How to avoid:** In `urls.py:row_url`, guard:
```python
def row_url(db, table, pk_values):
    if not pk_values:
        # use the rowid column (always first when primary_keys is empty)
        return None  # caller falls back to row.{rowid} from row data
```
And in templates: `{% if primary_keys %}{{ row_url(...) }}{% else %}/{{ db }}/{{ table }}/{{ row.rowid }}{% endif %}`.

**Warning sign:** 500 error on `/sglawwatch/about_singapore_law` page rendering.

### Pitfall 5: Compound primary keys need tilde encoding, not URL encoding

**What goes wrong:** A PK value containing `/` (e.g., a slug or path-like string) gets URL-encoded as `%2F`, but datasette's URL parser uses tilde encoding (`~2F`). The row endpoint 404s.

**Why it happens:** Datasette uses tilde encoding to avoid `%`-encoding ambiguity in path segments. `urllib.parse.quote(s, safe="")` produces `%2F` not `~2F`.

**How to avoid:** Port `datasette.utils.tilde_encode` directly (see Pattern 2 above). `[VERIFIED: utils/__init__.py:1173-1186]`

**Warning sign:** Row pages 404 for tables with non-trivial PK values.

### Pitfall 6: Hidden table reachable via direct URL

**What goes wrong:** `GET /sglawwatch/_zeeker_schemas` reaches the table-page handler, fetches the JSON (datasette serves it!), and renders. The `_zeeker_*` filter only fired on the database-page table list, not on the table-page handler.

**Why it happens:** Phase 4's filter was a list-comprehension on the database-page payload — it doesn't apply to the table-page route by default.

**How to avoid:** First line of `routes_table.py` and `routes_row.py` after path-param parsing:
```python
if table.startswith("_zeeker"):
    raise HTTPException(status_code=404, detail="Table not found")
```
Mirror logic for FTS internals: also `raise 404` when `table.endswith(("_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config"))`. Or, more robustly, fetch `/-/metadata.json` + the database payload and check `tables[table].hidden == True` — but that's an extra round-trip per request. The startswith check is a fast path; a missed FTS-internal still gets caught by the database-page filter which never links to it.

**Warning sign:** Verifier asserts `curl /sglawwatch/_zeeker_schemas` returns 404; if it returns 200, this filter is missing.

### Pitfall 7: Forwarding ALL query params to datasette opens an SSRF-ish surface

**What goes wrong:** Browser sends `?_extras=foreign_key_tables&allow_execute_sql=true` and gets back JSON with extra fields the template can use to surface unintended data.

**Why it happens:** Forwarding `dict(request.query_params)` indiscriminately means any datasette-internal flag a browser knows about is honored.

**How to avoid:** Allowlist. Only forward known query params: `_size, _sort, _sort_desc, _search, _next, _facet, _facet_array, _facet_date, _shape` and any column-name filters (those are arbitrary `colname=value`). Strip everything else before constructing the upstream request.

**Warning sign:** Threat-model review flags this as an issue; verifier doesn't catch it but unit tests should.

### Pitfall 8: Datasette returns 4xx not 404 for unknown table

**What goes wrong:** `GET /sglawwatch/no-such-table.json` returns 400 (or 200 with an error JSON) in some datasette versions, not a clean 404.

**Why it happens:** Datasette's table-not-found path varies; in 0.65.x it returns 404 with a JSON body `{"ok": false, "error": "..."}`, but the actual status code path in `views/table.py` can be a `Response(status=404)` or a `NotFound` exception that becomes 404. Either way, frontend should distinguish "table not found" from "server error".

**How to avoid:** In `fetch_table`, handle `r.status_code == 404` → return `None`; raise on other errors. Same pattern as `fetch_database` `[VERIFIED: datasette_client.py:30-40]`.

**Warning sign:** Unknown tables return 503 (data API down) instead of 404.

## Code Examples

### Extending `datasette_client.py`

```python
# Adapted from existing fetch_database pattern (datasette_client.py:30-40)
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
    safe_params = {"_shape": "objects"}
    for k, v in (params or {}).items():
        # Allowlist datasette-internal params
        if k in ALLOWED or "__" in k:  # column__exact / column__contains etc.
            safe_params[k] = v
        # Plain column-name filters (colname=value) are also allowlisted
        elif not k.startswith("_"):
            safe_params[k] = v
    r = await client.get(f"/{db}/{table}.json", params=safe_params)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


async def fetch_row(
    client: httpx.AsyncClient,
    db: str,
    table: str,
    pk: str,
) -> dict | None:
    """GET /{db}/{table}/{pk}.json — single row; None on 404."""
    r = await client.get(f"/{db}/{table}/{pk}.json", params={"_shape": "objects"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()
```

### Sort-toggle helper

```python
# packages/zeeker-frontend/src/zeeker_frontend/urls.py
def set_sort(path: str, qs: str, col: str, current_state: str | None) -> str:
    """Cycle: unsorted → asc → desc → unsorted.
    current_state: 'asc' if _sort=col, 'desc' if _sort_desc=col, None otherwise.
    """
    cleaned = path_with_removed_args(path, qs, {"_sort", "_sort_desc"})
    base_qs = cleaned.split("?", 1)[1] if "?" in cleaned else ""
    if current_state is None:
        return path_with_added_args(path, base_qs, {"_sort": col})
    if current_state == "asc":
        return path_with_added_args(path, base_qs, {"_sort_desc": col})
    # desc → clear
    return cleaned
```

### Table page route handler skeleton

```python
# packages/zeeker-frontend/src/zeeker_frontend/routes_table.py
from datetime import datetime
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from urllib.parse import urlparse

from zeeker_frontend.datasette_client import fetch_table, fetch_site_metadata

router = APIRouter()

_HIDDEN_TABLE_PREFIXES = ("_zeeker",)
_HIDDEN_TABLE_SUFFIXES = ("_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config")


@router.get("/{db}/{table}", response_class=HTMLResponse)
async def table_page(request: Request, db: str, table: str):
    # Pitfall 6 — block hidden tables at the route boundary
    if table.startswith(_HIDDEN_TABLE_PREFIXES) or table.endswith(_HIDDEN_TABLE_SUFFIXES):
        raise HTTPException(status_code=404, detail="Table not found")

    client: httpx.AsyncClient = request.app.state.http
    try:
        payload = await fetch_table(client, db, table, dict(request.query_params))
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="Data API unavailable")
    if payload is None:
        raise HTTPException(status_code=404, detail="Table not found")

    site_metadata = await fetch_site_metadata(client)
    table_meta = (
        (site_metadata.get("databases") or {})
        .get(db, {}).get("tables", {}).get(table, {})
    )
    display = table_meta.get("display") or {}

    # Pitfall 2 — strip host from datasette next_url, repoint to HTML route
    next_url = None
    if payload.get("next_url"):
        parsed = urlparse(payload["next_url"])
        if parsed.query:
            next_url = f"/{db}/{table}?{parsed.query}"

    response = request.app.state.templates.TemplateResponse(
        request=request,
        name="table.html",
        context={
            "database": db,
            "table": table,
            "rows": payload["rows"],
            "columns": payload["columns"],
            "primary_keys": payload.get("primary_keys") or [],
            "facet_results": payload.get("facet_results") or {},
            "filtered_table_rows_count": payload.get("filtered_table_rows_count"),
            "next_url": next_url,
            "request_qs": request.url.query,
            "table_mode": display.get("table_mode") or "tabular",
            "display": display,
            "table_meta": table_meta,
            "metadata": _merge_metadata(site_metadata, db, table, payload),
            "breadcrumbs": [
                {"href": f"/{db}", "label": _db_title(site_metadata, db)},
                {"label": table_meta.get("title") or table},
            ],
            "current_year": datetime.now().year,
        },
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response
```

## Phase 5 Verifier Script Outline (`scripts/verify_phase_05.sh`)

Mirror `verify_phase_04.sh`. Sections:

```
A. Phase-4 invariants (delegate to verify_phase_04.sh)

B. Table page renders feed mode (sglawwatch/headlines)
   - 200 OK
   - Contains '<article class="va-item"' (feed card)
   - Contains 'class="cat-pill'
   - Contains '/static/css/zeeker.css' (frontend CSS)
   - DOES NOT contain 'zeeker-base.css' (no datasette HTML leak)
   - Italic-accent H1
   - Cache-Control: max-age=60, swr=300

C. Table page renders tabular mode (default fallback — choose a hintless table)
   - 200 OK
   - Contains '<table class="data-table"'
   - Header columns rendered as <th> with sortable links

D. Facet sidebar renders (sglawwatch/headlines?_facet=category)
   - 200 OK
   - Contains 'class="facets"'
   - Contains 'class="facet-block"'
   - Contains the facet column name + at least one facet value

E. Applied-facet chips render (sglawwatch/headlines?category=Straits+Times)
   - 200 OK
   - Contains 'class="filter-chip"'
   - Chip text contains "Straits Times"
   - Chip has a clear-link/×

F. Pagination renders (sglawwatch/headlines?_size=2 — small page forces next_url)
   - 200 OK
   - Contains 'class="pagination"'
   - Contains 'Next →' anchor with href starting "/sglawwatch/headlines?"
   - Contains "Show: 25 · 50 · 100"

G. FTS forwards (sglawwatch/headlines?_search=DBS)
   - 200 OK
   - Contains a search-applied chip
   - Result count > 0 (or 'No results for' if zero matches in the test DB)

H. Sort toggle (sglawwatch/headlines?_sort=date)
   - 200 OK
   - Header with sort indicator (↑ or ↓ arrow)
   - Subsequent click cycles to ?_sort_desc=date (verify with second curl)

I. Export anchors are direct (NOT proxied through frontend)
   - Body contains href="/sglawwatch/headlines.csv" and href="/sglawwatch/headlines.json"
   - curl -I /sglawwatch/headlines.csv → 200 + Content-Type: text/csv
     (this hits Caddy → datasette; verifies Phase-3 routing intact)

J. Row page renders article mode (sglawwatch/headlines/{any-pk-from-baseline})
   - 200 OK
   - Contains 'class="article"'
   - Contains 'class="aside"'
   - Contains italic-accent H1

K. Row page renders tabular fallback (a table without row_mode hint)
   - 200 OK
   - Contains '<dl' (key-value)
   - Long-text fields wrapped in <details>

L. Hidden tables blocked at route boundary
   - curl /sglawwatch/_zeeker_schemas → 404
   - curl /sglawwatch/headlines_fts → 404

M. Phase-6 boundary asserts (still 404 — these belong to Phase 6)
   - curl /-/sql → datasette HTML 200 (preserved through Caddy /-/* routing — NOT frontend)
     (this is a positive routing assertion — /-/* is datasette territory)
   - curl /developers → 404 from frontend (Phase 6 will port this)
   - curl /-/search → datasette HTML or 404, but NEVER frontend (Phase 6 will port at /-/search)
   - curl /status → 404 from frontend (Phase 6)
   - curl /sources → 404 from frontend (Phase 6)
   - curl /about → 404 from frontend (Phase 6)

N. Empty / error paths
   - curl /sglawwatch/no-such-table → 404
   - curl /sglawwatch/headlines/non-existent-pk-12345 → 404
   - curl /sglawwatch/headlines?_search=___zzzzzzz → 200, body contains "No results for"
   - curl /sglawwatch/headlines/{nested}/extra → 404 (deeper paths reject)

O. API parity (delegate to verify_api_parity.sh against phase-03-pre baseline)
```

Implementation guidance: copy `verify_phase_04.sh` verbatim and substitute the Phase-4 sections. The structural pattern (BODY=$(curl...) → grep) is identical. Reuse `tr '\n' ' ' | grep -qE` for cross-line H1 matching (Phase-4 lesson).

## Phase-6 Boundary Assertions

Phase 5 must NOT regress these — they all belong to Phase 6:

| URL | Expected status | Rationale |
|-----|----------------|-----------|
| `/-/sql` | 200 (datasette HTML) | `/-/*` matches Caddy `@datasette`; goes to datasette directly. Phase 6 ports this. |
| `/-/search` | 200 (datasette HTML) | Same as above |
| `/-/versions.json` | 200 (datasette JSON) | `/-/*` |
| `/developers` | 404 (frontend) | Plain HTML route, no Caddy match → frontend → no handler → 404. Phase 6 ports. |
| `/status` | 404 (frontend) | Same |
| `/sources` | 404 (frontend) | Same |
| `/about` | 404 (frontend) | Same |
| `/how-to-use` | 404 (frontend) | Same |
| `/llms.txt` | 404 (frontend) | Same |

The verifier's section M asserts each. **404 from frontend is the correct state for Phase 5**; getting 200 means a route was accidentally registered.

## Empty / Error Path Specification

| Scenario | Expected response | Body |
|----------|------------------|------|
| Unknown table (`/{db}/no-such-table`) | 404 HTML | UI-SPEC §Copywriting: "Table not found. The table 'no-such-table' does not exist in the '{db}' database." |
| Unknown row (`/{db}/{table}/no-such-pk`) | 404 HTML | UI-SPEC §Copywriting: "Record not found. No row with primary key 'no-such-pk' in '{table}'." |
| Empty table (`/{db}/empty_table`) | 200 HTML | UI-SPEC §Copywriting: "No records found / This table has no data yet…" |
| Empty FTS (`/{db}/{table}?_search=zzz`) | 200 HTML | UI-SPEC §Copywriting: "No results for 'zzz' in {table title}…" |
| Malformed querystring (`/{db}/{table}?_size=NaN`) | 200 HTML (datasette ignores invalid `_size` and falls back to default) OR 400 if datasette returns one | Same page; if datasette 400s, frontend converts to 400 with a generic "Bad request" |
| Hidden table (`/{db}/_zeeker_schemas`) | 404 HTML | Standard 404 (don't reveal that the table exists but is hidden) |
| Datasette down (httpx HTTPError) | 503 HTML | Standard 503 ("Data API unavailable") — same as routes_database.py's pattern |
| Compound-PK row with bad encoding | 404 HTML | datasette returns 404 for invalid tilde sequence |
| Path with extra segments (`/{db}/{table}/{pk}/extra`) | 404 (FastAPI router doesn't match) | Standard FastAPI 404 |

## Validation Architecture

> Required by Nyquist gate (workflow.nyquist_validation absent in config = enabled).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 + pytest-httpx 0.36.0 (already installed Phase 4) |
| Config file | `packages/zeeker-frontend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd packages/zeeker-frontend && uv run pytest -q tests/test_table.py tests/test_row.py tests/test_urls.py -x` |
| Full suite command | `cd packages/zeeker-frontend && uv run pytest -q` |
| Verifier script | `scripts/verify_phase_05.sh` (gated by full suite green) |

### Test Pyramid

| Layer | Scope | Assertions | Approx tests |
|-------|-------|-----------|--------------|
| **Unit (urls.py)** | Querystring helpers — pure functions | `path_with_added_args` adds keys; `path_with_replaced_args` replaces; `path_with_removed_args` removes; `tilde_encode` matches datasette behavior; `set_sort` cycles asc→desc→clear; `row_url` handles compound + rowid-fallback PKs | 12-15 tests |
| **Unit (datasette_client.py)** | `fetch_table` + `fetch_row` allowlist + 404 + 503 paths | Allowlist filters out unknown params; 404 returns None; non-404 errors raise; `_shape=objects` always added; column__contains pattern allowed | 6-8 tests |
| **Integration (test_table.py)** | Full route via ASGITransport + MockTransport | feed mode renders `.va-item`; tabular fallback renders `.data-table`; facet sidebar renders `.facets`; applied-facet chip renders `.filter-chip`; pagination Next link present when next_url; FTS no-results message; sort header link cycles; export hrefs are direct (`/db/table.csv?...`); hidden table 404; unknown table 404; Cache-Control header; italic-accent H1; rows render via `_shape=objects` (templates use row.colname) | 14-18 tests |
| **Integration (test_row.py)** | Full route via ASGITransport + MockTransport | article mode renders `.article` + `.aside`; judgment mode renders `.dateline`; longform mode renders no aside; tabular fallback renders `<dl>` + `<details>` for long fields; unknown row 404; rowid-PK fallback works (about_singapore_law fixture); compound-PK route works (synthetic fixture); Cache-Control | 9-11 tests |
| **Verifier script (`verify_phase_05.sh`)** | End-to-end against the running docker stack | All 14 sections A–O above. Includes negative routing, structural HTML asserts, hidden-table block, Phase-6 boundary, API parity delegation | ~40 individual asserts |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| REQ-frontend-route-set | `/{db}/{table}` returns 200 | integration | `pytest tests/test_table.py::test_table_returns_200_feed_mode -x` | Wave 0 |
| REQ-frontend-route-set | `/{db}/{table}/{pk}` returns 200 | integration | `pytest tests/test_row.py::test_row_returns_200_article_mode -x` | Wave 0 |
| REQ-frontend-data-via-http | No sqlite3 import in routes | static check | `grep -r "import sqlite3\|from sqlite3" packages/zeeker-frontend/src/zeeker_frontend/` | n/a |
| REQ-eliminate-template-drift | One generic table.html | structural | `find templates -name "_table-*"  | wc -l → 0` (asserted in verify_phase_05.sh) | Wave 0 |
| REQ-api-byte-parity | `.csv`/`.json` URLs unchanged | parity | `verify_api_parity.sh` (delegated from verify_phase_05.sh) | exists |
| D-01 (no per-table overrides) | No `_table-*` files in frontend templates dir | structural | `! find packages/zeeker-frontend/src/zeeker_frontend/templates -name "_table-*.html" \| read` (verifier) | n/a |
| D-04 (tabular fallback) | Tables without display hint render `<table class="data-table">` | integration | `pytest tests/test_table.py::test_table_tabular_fallback -x` | Wave 0 |
| D-05 (export direct) | `<a href="/{db}/{table}.csv?...">` exists in body, NOT proxied through frontend | integration + verifier | `pytest tests/test_table.py::test_export_anchors_are_direct -x` + verifier section I | Wave 0 |
| D-06 boundary (no SQL editor) | No `<form>` with `_sql` action; `/-/sql` 404 from frontend | verifier | verifier section M | n/a |
| Pitfall 4 (rowid PKs) | Tables with `primary_keys: []` render row links | integration | `pytest tests/test_table.py::test_rowid_pk_fallback -x` | Wave 0 |
| Pitfall 6 (hidden table 404) | `_zeeker_*` and `*_fts` 404 at route entry | integration + verifier | `pytest tests/test_table.py::test_hidden_table_blocked -x` + verifier L | Wave 0 |
| Phase-6 boundary | `/developers` 404 from frontend; `/-/sql` reaches datasette | verifier | verifier section M | exists (delegate) |

### Sampling Rate
- **Per task commit:** quick run command (table + row + urls test files only; ~30 tests; <5s)
- **Per wave merge:** full suite (`uv run pytest -q`; ~80+ tests after Phase 5 lands; <10s)
- **Phase gate:** Full suite green AND `verify_phase_05.sh` exit 0 against docker stack

### Wave 0 Gaps
- [ ] `packages/zeeker-frontend/tests/test_urls.py` — covers urls.py helpers (NEW file)
- [ ] `packages/zeeker-frontend/tests/test_table.py` — covers routes_table.py (NEW file)
- [ ] `packages/zeeker-frontend/tests/test_row.py` — covers routes_row.py (NEW file)
- [ ] `packages/zeeker-frontend/tests/fixtures/headlines_table.json` — captured `/sglawwatch/headlines.json?_shape=objects&_size=10&_facet=category` payload (or hand-crafted with same shape)
- [ ] `packages/zeeker-frontend/tests/fixtures/headlines_row.json` — captured `/sglawwatch/headlines/{pk}.json?_shape=objects` payload
- [ ] `packages/zeeker-frontend/tests/fixtures/about_singapore_law_table.json` — for rowid-PK test (table without declared PK)
- [ ] `packages/zeeker-frontend/tests/fixtures/judgments_row.json` — for judgment row mode test (synthetic; live data may not have judgments yet)
- [ ] `packages/zeeker-frontend/tests/fixtures/metadata.json` (UPDATE existing) — add `display.*` blocks for the 3 in-scope tables so route handlers see them in mock data

Framework already installed (Phase 4); no install commands needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All | ✓ | 3.12 (verified `.venv/lib/python3.12`) | — |
| pytest 9.0.3 | All tests | ✓ | 9.0.3 (Phase 4) | — |
| pytest-asyncio 1.3.0 | Async route tests | ✓ | 1.3.0 (Phase 4) | — |
| pytest-httpx 0.36.0 | MockTransport | ✓ | 0.36.0 (Phase 4) | — |
| FastAPI | Frontend | ✓ | (Phase 4 pinned) | — |
| httpx | Datasette client | ✓ | (Phase 4 pinned) | — |
| Jinja2 | Templates | ✓ | (Phase 4 pinned) | — |
| Docker daemon | verify_phase_05.sh end-to-end | ✗ (verified not running 2026-04-25) | — | Tests use ASGITransport + MockTransport (no docker needed); verifier defers to live-stack run at human checkpoint |
| Live datasette stack | API parity check | ✗ (verified not running 2026-04-25) | — | Captured baselines under `.planning/baselines/phase-03-pre/` are usable for fixture creation; verifier API-parity step runs only when local stack is up (`BASE_URL=http://localhost`) |
| `gh` CLI | Not used in this phase | n/a | — | — |

**Missing dependencies with no fallback:** None — all unit/integration tests run without docker.

**Missing dependencies with fallback:**
- Docker / live stack — only the verifier's section O (API parity) and end-to-end smoke run require it. Plans 05-01 through 05-04 are docker-free; plan 05-05 (verifier + metadata + checkpoint) brings up docker for the final smoke. Same as Phase 4's pattern.

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json` → enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Public read-only data; no login |
| V3 Session Management | no | Stateless |
| V4 Access Control | yes | Hidden-table filter at route boundary blocks `_zeeker_*` and FTS internals; allowlisted querystring forwarding to datasette |
| V5 Input Validation | yes | Querystring allowlist; FastAPI path-param regex on `db`/`table`/`pk`; httpx `base_url` pinning prevents SSRF |
| V6 Cryptography | no | No crypto in this phase |
| V7 Errors and Logging | yes | 503 on httpx error (no traceback exposure); 404 on missing data (no info disclosure differentiating "hidden" vs "missing") |
| V8 Data Protection | partial | All data is public; no PII handling |

### Known Threat Patterns for FastAPI/Jinja/httpx stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via row data, column names, table descriptions | Tampering | Jinja2Templates autoescape ON (Phase-4 carry-forward, verified main.py:70); never use `\|safe` on dataset-supplied content; the M1 partial uses `striptags` which we preserve |
| SSRF via `db` / `table` / `pk` path params | Tampering | FastAPI path-param regex blocks `/`; httpx `base_url` pinning means even if `db == "../../etc/passwd"`, the upstream URL is `http://zeeker-datasette:8001/../../etc/passwd.json` which datasette returns 404 for |
| URL parameter smuggling (extra `_extras=foreign_key_tables` reveals data) | Tampering / Info disclosure | Querystring allowlist in `fetch_table` (Pitfall 7) — only known datasette-internal flags forwarded |
| DoS via long `?_search` or unbounded `_size` | DoS | httpx Timeout(10.0, connect=2.0) (Phase-4 carry-forward); datasette has its own row-cap and query-time limits; `_size` capped server-side |
| Cache poisoning via metadata cache | Info disclosure | TTL 60s; cache key is constant (no user input); already accepted-risk in Phase 4 |
| 500 traceback disclosure | Info disclosure | Explicit `HTTPException(503)` on httpx error; FastAPI default 404 / 500 responses are JSON without trace |
| Hidden-table reveal | Info disclosure | Both `_zeeker_*` and `*_fts*` blocked at route boundary; same 404 message regardless of "hidden" vs "missing" so timing/wording doesn't reveal existence |
| `<mark>` highlight injection if implemented from row text | XSS | Either skip highlight (recommended) or use `<mark>{{ value\|striptags }}</mark>` with autoescape on |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Datasette template `_table-{db}-{table}.html` partial seam | One generic `table.html` driven by metadata `display.*` hints | M2 Phase 5 (this phase) | Eliminates 11 M1 partial files; future-proofs Phase 7 pruning |
| Datasette HTML rendering with `app.css` specificity wars | FastAPI/Jinja with own `zeeker.css` — no `app.css` in the loop | M2 Phase 4–5 | Footer link visibility bug class eliminated |
| `?_shape=arrays` (datasette default) for JSON | Frontend requests `?_shape=objects` | this phase | Templates index by column name; no `zip(columns, row)` boilerplate |
| `_search_highlight` (assumed in UI-SPEC / CONTEXT) | **Does not exist in datasette 0.65.x** | already current | Highlight is client-side or skipped |
| Datasette 1.0 row-endpoint shape (`{ok, row, primary_key_values}`) | 0.65.x shape (`{database, table, rows: [[...]], columns, primary_keys, primary_key_values}`) | datasette 1.0 future | Plans target 0.65.x; future migration to 1.0 is its own phase |

**Deprecated/outdated:**
- M1 `_table-{db}-{table}.html` partials — reference only; not ported. Their column-slot pattern informs the `display.columns` schema instead.
- `default:table.html` Jinja extends syntax — Datasette-only; replaced by `{% extends "base.html" %}`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | UI-SPEC's `<mark>` from `_search_highlight` is intended; downgrade to "skip highlight in v1 OR client-side JS" matches user intent | §Pitfall 3 | If user wanted highlight as v1 must-have, planner adds JS module — small scope creep |
| A2 | Display hints land in **base** `metadata.json` (not per-database S3 overlay) for the 3 explicitly mapped tables | §Display-Hint Schema Confirmation | If user wants overlay-based hints, plan 05-05 needs to coordinate with the S3 overlay generator (`zeeker assets generate`) — adds Phase-7 coupling |
| A3 | `?_shape=objects` is supported by datasette 0.65.2 and returns `rows: list[dict]` keyed by column name | §Pattern 1, §Datasette JSON Contract | If shape is broken/unsupported in 0.65.x specifically, fall back to default `arrays` shape and add a `zip(columns, row)` Jinja filter — adds 5 lines but no architectural change |
| A4 | The 8 sg-gov-newsrooms `*_news` tables all map cleanly to `feed`/`article` modes with the column slots derived from M1 partials | §Display-Hint Schema Confirmation | If a specific `*_news` table has a different column shape, that table renders `tabular` until its hint is added — graceful |
| A5 | The Phase-6 boundary URLs (`/developers`, `/status`, etc.) are not yet handled by any frontend route in `main.py` | §Phase-6 Boundary Assertions | If Phase-4 or earlier accidentally registered one, the 404 assertion fails — verifier catches this. Reviewed `main.py` at research time: only `home_router` + `database_router` + `/frontend-test` mounted; safe |
| A6 | Tables with no declared PK (rowid-only) are reachable at `/{db}/{table}/{rowid_value}` and datasette resolves via implicit rowid | §Pitfall 4 | If datasette doesn't resolve rowid this way for the row endpoint, the row link from `about_singapore_law` table page 404s — fixture-based unit test catches |

## Open Questions (RESOLVED)

1. **`<mark>` highlight policy for FTS results**
   - What we know: UI-SPEC §Interaction Contracts and CONTEXT §Claude's Discretion both reference `_search_highlight`; that field doesn't exist in datasette 0.65.x JSON.
   - What's unclear: Does the user want client-side JS highlight (adds ~30 LoC of JS), or accept "skip highlight in v1, document as gap"?
   - Recommendation: Skip highlight in v1; planner surfaces this as Plan 05-02 Claude's-discretion item. If user later finds scanning fatigue painful, add JS in Phase 6.
   - **RESOLVED:** Adopted in Plan 05-02 threat T-05-04 (FTS `<mark>` highlight NOT implemented in v1; Jinja autoescape preserved on all row content) and surfaced for manual sweep via the Phase-5 VALIDATION.md / 05-DEPLOY-NOTES.md operator checklist. Deferred to Phase 6 if scanning fatigue is observed in production.

2. **`suggested_facets` rendering**
   - What we know: Datasette's JSON exposes a `suggested_facets` list of "you might want to facet on this" hints.
   - What's unclear: Should the sidebar render these as "Add facet" CTAs, or is the explicit `?_facet=col` URL the only way to get a facet to show?
   - Recommendation: Phase 5 ignores `suggested_facets`; user must opt-in to a facet by adding `?_facet=col` to the URL. Future enhancement.
   - **RESOLVED:** Adopted in Plan 05-02 Task 1 (handler passes `suggested_facets` into the template context as a no-op for forward compatibility) and Plan 05-02 Task 2 (table.html / facet_sidebar.html consume only `payload.facet_results`; `suggested_facets` is ignored at render time). Future enhancement deferred to Phase 6.

3. **`metadata.json` edits — who owns the diff?**
   - What we know: D-02 says display hints live in metadata.json; the file is in repo root (`metadata.json`).
   - What's unclear: Plan 05-05 will edit `metadata.json` to add 3 `display.*` blocks. Is this a project-instructions-clean-edit (touches one file) or does it need to coordinate with S3 overlay regeneration?
   - Recommendation: Edit base `metadata.json` directly; the file is loaded by datasette at startup; no S3 overlay change needed for Phase 5. Plan should call out the file rename / edit explicitly so reviewer notices.
   - **RESOLVED:** Adopted in Plan 05-05 Task 1 (single edit to base `metadata.json` adding 11 `display.*` blocks; no S3 overlay coordination needed — datasette loads `metadata.json` at startup directly from the repo root).

4. **Compound-PK fixture for testing**
   - What we know: All in-scope tables (sglawwatch.headlines, sglawwatch.about_singapore_law, Zeeker-Judgements.judgments, sg-gov-newsrooms.*_news) have single-column PKs (or no PK = rowid).
   - What's unclear: Without a compound-PK table in current data, the compound-PK URL helper is unit-tested but not integration-tested.
   - Recommendation: Plan 05-01 includes a synthetic test fixture for compound PK + tilde encoding (no live data dependency).
   - **RESOLVED:** Adopted in Plan 05-01 Task 2 (`test_compound_pk_tilde_encodes_each` — synthetic fixture exercising compound-PK tilde encoding without live-data dependency, since no in-scope Phase-5 table has a compound PK).

## Sources

### Primary (HIGH confidence)
- **Datasette 0.65.2 source** (`.venv/lib/python3.12/site-packages/datasette/`) — verified table response shape (`views/table.py:786-808`), row response shape (`views/row.py:80-102`), URL helpers (`utils/__init__.py:268-331`), tilde encoding (`utils/__init__.py:1173-1186`), array facet (`facets.py:290-455`)
- **Captured live baselines** (`.planning/baselines/phase-03-pre/`) — `sglawwatch_headlines.json__size_10.json` confirmed actual response shape including `facet_results.category`, `next_url` format, `primary_keys: []` for `about_singapore_law`
- **Phase 4 SUMMARY chain** (`.planning/phases/04-port-home-database-pages/04-{01,03,04,05}-SUMMARY.md`) — locked patterns for routes, MockTransport tests, app.state.templates, CSS section delimiter, verifier shape
- **Phase 5 CONTEXT.md + UI-SPEC.md** — locked decisions D-01..D-06 + design contract
- **sketch-findings-zeeker-datasette skill** (auto-loaded) — palette, typography, spacing, component CSS for facet sidebar / row reading layouts / shell chrome

### Secondary (MEDIUM confidence)
- **Datasette docs** (`https://docs.datasette.io/en/0.65.2/json_api.html`) — confirmed `_shape` parameter values; documentation incomplete on `_search_highlight` (cross-verified by source-code grep showing field doesn't exist)
- **PRD §11 R1** — facet edge cases (array, m2m) confirmed and validated against datasette source

### Tertiary (LOW confidence)
- **Web search for `_search_highlight`** — no authoritative source found; concluded the field does not exist in 0.65.x by negative source-grep evidence (HIGH negative confidence after verification)

## Metadata

**Confidence breakdown:**
- Datasette JSON contract: HIGH — verified against source + captured baselines
- Standard stack: HIGH — entire stack is Phase-4 carry-forward; no new deps
- Architecture patterns: HIGH — extends Phase-4's two-route pattern; same MockTransport tests
- M1 CSS harvest: MEDIUM — only feed-cards CSS lives in M1; ~270 lines of new CSS must be authored fresh from sketch references (which themselves are HIGH-confidence locked decisions)
- Display-hint schema: HIGH — confirmed by reading existing metadata.json; nests cleanly without conflict
- Pitfalls (1, 2, 4, 5, 6): HIGH — directly verified against source / fixtures
- Pitfall 3 (no `_search_highlight`): HIGH for the negative claim — multi-source verified
- Test pyramid: HIGH — same framework + patterns as Phase 4
- Verifier shape: HIGH — direct adaptation of `verify_phase_04.sh`

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days; Datasette 0.65.x is stable, sketch-findings skill is locked)

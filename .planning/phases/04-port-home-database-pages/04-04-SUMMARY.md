---
phase: 04-port-home-database-pages
plan: "04"
subsystem: zeeker-frontend
tags:
  - m2
  - frontend
  - database-page
  - jinja2
  - fastapi-routes
  - tdd
dependency_graph:
  requires:
    - packages/zeeker-frontend/src/zeeker_frontend/main.py (04-01)
    - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py (04-01)
    - packages/zeeker-frontend/src/zeeker_frontend/templates/base.html (04-01)
    - packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css (04-02)
    - packages/zeeker-frontend/src/zeeker_frontend/routes_home.py (04-03)
  provides:
    - packages/zeeker-frontend/src/zeeker_frontend/routes_database.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/database.html
  affects:
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
    - packages/zeeker-frontend/tests/test_database.py
    - packages/zeeker-frontend/tests/fixtures/sglawwatch.json
tech_stack:
  added: []
  patterns:
    - "Single-predicate hidden filter: [t for t in tables if not t.get('hidden')] — covers _zeeker_* AND FTS internals (eliminates M1's faulty dual-check)"
    - "APIRouter with HTMLResponse — route module owns only its handler, app.state.templates replaces direct import"
    - "MockTransport ASGITransport integration test (no docker)"
    - "Cache-Control public, max-age=60, stale-while-revalidate=300 header set in handler"
key_files:
  created:
    - packages/zeeker-frontend/src/zeeker_frontend/routes_database.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/database.html
    - packages/zeeker-frontend/tests/test_database.py
  modified:
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
    - packages/zeeker-frontend/tests/fixtures/sglawwatch.json
decisions:
  - "Single-predicate filter (not t.get('hidden')) preferred over M1's dual-check (hidden + startswith('_zeeker')) — Datasette marks ALL internal tables hidden=true including FTS; prefix check would miss FTS internals"
  - "sglawwatch.json fixture updated to include realistic hidden tables (_zeeker_schemas, _zeeker_metadata, headlines_fts, headlines_fts_data, headlines_fts_idx) so filter tests exercise real data shapes"
  - "Jinja rfind() split for italic-accent H1 — last word italicized, remainder plain; matches M1 WARN-04 pattern"
  - "Canned queries passed as list from payload.get('queries', []) — handles both dict and list shapes defensively"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-04-22"
  tasks_completed: 1
  files_changed: 5
---

# Phase 4 Plan 04: Database Overview Page Summary

**GET /{db} handler with MockTransport integration tests — M1 database.html ported to FastAPI/Jinja, single-predicate hidden filter replacing M1's faulty dual-check, editorial-row table list, italic-accent H1, 7/7 tests green, Cache-Control header set.**

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write routes_database.py + database.html port + test_database.py + wire into main.py | 25829c7 | routes_database.py, database.html, main.py, test_database.py, fixtures/sglawwatch.json |

## Test Results

- **39 tests passed** (7 new in test_database.py + 32 prior), 0 failed, 0 errors
- `test_database_returns_200_with_editorial_list` — 200, db-header, db-statband, .list, headlines table, zeeker.css ref, no zeeker-base.css
- `test_database_unknown_returns_404` — GET /no-such-database returns 404, not 500
- `test_database_filters_hidden_zeeker_tables` — _zeeker_schemas, _zeeker_metadata absent from rendered HTML
- `test_database_filters_fts_tables` — headlines_fts, headlines_fts_data, headlines_fts_idx absent from rendered HTML
- `test_database_italic_accent_h1` — `<h1>…<em>…</em>…</h1>` pattern confirmed
- `test_database_cache_control_header` — max-age=60, stale-while-revalidate=300 confirmed
- `test_database_renders_breadcrumb` — `class="db-crumb"` present in rendered output

## Jinja Binding Port Map Applied

| M1 original | Post-port | Reason |
|-------------|-----------|--------|
| `{% extends "default:database.html" %}` | `{% extends "base.html" %}` | Remove datasette prefix |
| `{% block extra_head %}{{ super() }}` | `{% block head %}` | base.html head block is neutral (no super needed) |
| `{% block nav %}{% set breadcrumbs = [...] %}{% include "_header.html" %}{% endblock %}` | DELETED | Handler passes breadcrumbs in context; base.html renders nav + breadcrumb |
| `{% for t in tables if not t.hidden and not t.name.startswith('_zeeker') %}` | Handler filters: `[t for t in payload.get("tables", []) if not t.get("hidden")]` | Single-predicate covers ALL hidden tables (RESEARCH Pitfall 5) |
| `{% set table_meta = metadata.get('tables', {}).get(table.name) or {} %}` | `{% set table_meta = (metadata.tables[table.name] if metadata and metadata.tables and table.name in metadata.tables else {}) %}` | Avoid KeyError on Starlette strict Jinja |
| `{% block footer %}{% include "_footer.html" %}{% endblock %}` | DELETED | base.html renders footer |

## Critical Filter Change

**M1's faulty dual-check (eliminated):**
```jinja
{% for t in tables if not t.hidden and not t.name.startswith('_zeeker') %}
```

**Post-port single predicate (in handler, not template):**
```python
visible_tables = [t for t in payload.get("tables", []) if not t.get("hidden")]
```

This satisfies RESEARCH Pitfall 5: Datasette marks ALL internal tables as `hidden=true` — including FTS internals (`*_fts`, `*_fts_data`, `*_fts_docsize`, `*_fts_idx`). The M1 prefix check would miss FTS tables, leaking them into the rendered table list. The single predicate is both simpler and correct.

## Fixture Update

`tests/fixtures/sglawwatch.json` was updated to include realistic hidden tables:
- `headlines_fts`, `headlines_fts_data`, `headlines_fts_idx` — FTS internals with `hidden: true`
- `_zeeker_schemas`, `_zeeker_metadata` — internal metadata tables with `hidden: true`
- Visible tables unchanged: `about_singapore_law`, `case_summaries`, `headlines`

This ensures filter tests (`test_database_filters_hidden_zeeker_tables`, `test_database_filters_fts_tables`) exercise real data shapes from the Datasette API.

## Datasette Field-Shape Notes

- `queries` field: the captured sglawwatch.json returns `{}` (dict), not `[]` (list). `payload.get("queries", [])` handles both gracefully — empty dict is falsy in Jinja `{% if canned_queries %}`.
- `fts_table` field present on `headlines` table pointing to `headlines_fts` (hidden). The template checks `table.fts_table or table.fts` for M1 compatibility (some Datasette versions use `fts`, others `fts_table`).
- `primary_keys` field: not present in captured fixture — template guard `(table.primary_keys or [])` handles gracefully.

## main.py: Parallel-Safe Router Mounting

Both 04-03 (home) and 04-04 (database) touch main.py. The database router is appended immediately after the home router — co-located for clarity:

```python
from zeeker_frontend.routes_home import router as home_router
from zeeker_frontend.routes_database import router as database_router
app.include_router(home_router)
app.include_router(database_router)
```

FastAPI resolves `/` before `/{db}` (static paths win over parameterized), so include order does not affect route matching.

## Deviations from Plan

None — plan executed exactly as written. All 7 test cases pass with precise fixture shapes.

## Known Stubs

None — all template bindings are wired to real handler data. The `/{db}/{table}` links render correctly but return 404 from the frontend until Phase 5 ports the table-browse route. This is intentional and expected per plan.

## Downstream

- **Plan 04-05**: runs `verify_phase_04.sh` against the live stack and handles production deploy + rollback
- **Phase 5 hook**: `/{db}/{table}` 404 is expected and intentional — do not fix in this plan

## Threat Register Enforcement

| Threat | Status |
|--------|--------|
| T-04-04-01 SSRF via db param | Enforced — FastAPI path param regex blocks `/`; httpx base_url pins host |
| T-04-04-02 XSS via table names/descriptions | Enforced — Jinja autoescape ON; no `\|safe` on dataset-supplied content |
| T-04-04-03 PII leak via hidden tables | Enforced — single-predicate filter; verified by test_database_filters_hidden_zeeker_tables + test_database_filters_fts_tables |
| T-04-04-04 Hanging datasette DoS | Enforced — httpx.Timeout(10.0) from 04-01; 503 on timeout |
| T-04-04-05 500 stack trace on unknown db | Enforced — fetch_database returns None → HTTPException(404); verified by test_database_unknown_returns_404 |
| T-04-04-06 Cache poisoning | Accepted — public content, process-local, TTL 60s |
| T-04-04-07 SSTI | Accepted — template path is hardcoded literal |
| T-04-04-08 allow_execute_sql field | Accepted — public field, not rendered |

## Threat Flags

None — no new network endpoints or auth paths introduced beyond what the plan specified. GET /{db} is a public read-only route; `db` path parameter is user-controlled but sandboxed by FastAPI route matcher + httpx base_url pinning.

## Self-Check: PASSED

- `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py` — FOUND
- `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` — FOUND
- `packages/zeeker-frontend/tests/test_database.py` — FOUND
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` contains `app.include_router(database_router)` — VERIFIED
- `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py` contains `not t.get("hidden")` — VERIFIED
- Commit `25829c7` — FOUND
- 39 tests pass (7 new + 32 prior), 0 fail

---
phase: 04-port-home-database-pages
plan: "03"
subsystem: zeeker-frontend
tags:
  - m2
  - frontend
  - home
  - jinja2
  - fastapi-routes
  - tdd
dependency_graph:
  requires:
    - packages/zeeker-frontend/src/zeeker_frontend/main.py (04-01)
    - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py (04-01)
    - packages/zeeker-frontend/src/zeeker_frontend/templates/base.html (04-01)
    - packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css (04-02)
  provides:
    - packages/zeeker-frontend/src/zeeker_frontend/routes_home.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/index.html
  affects:
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
    - packages/zeeker-frontend/tests/test_home.py
tech_stack:
  added: []
  patterns:
    - "APIRouter with HTMLResponse — route module owns only its handler, app.state.templates replaces direct import"
    - "MockTransport ASGITransport integration test (no docker)"
    - "_filter_wildcard() defensive strip of Datasette * wildcard metadata key"
key_files:
  created:
    - packages/zeeker-frontend/src/zeeker_frontend/routes_home.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/index.html
    - packages/zeeker-frontend/tests/test_home.py
  modified:
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
decisions:
  - "app.state.templates preferred over direct import of templates from main.py — avoids circular import when 04-04 also adds a router to the same file"
  - "visible_dbs filtering done in handler (not template) for cleaner template logic; template only receives pre-filtered list"
  - "database.size|filesizeformat card chip preserved but conditionally rendered (Assumption A6: size absent from /.json today — matches M1 behaviour)"
metrics:
  duration: "~2 minutes"
  completed_date: "2026-04-21"
  tasks_completed: 1
  files_changed: 4
---

# Phase 4 Plan 03: Home Page Route + Template Summary

**GET / handler with MockTransport integration tests — ported M1 index.html extends base.html, petrol stat band, card grid, italic-accent H1, 5/5 tests green, Cache-Control header set.**

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write routes_home.py + index.html port + test_home.py + wire into main.py | 896d222 | routes_home.py, index.html, main.py, test_home.py |

## Test Results

- **32 tests passed** (5 new in test_home.py + 27 prior), 0 failed, 0 errors
- `test_home_returns_200_with_card_grid` — 200, db-statband, cards, H1+em, zeeker.css ref, no zeeker-base.css
- `test_home_sets_cache_control` — max-age=60, stale-while-revalidate=300 confirmed
- `test_home_filters_wildcard_databases_key` — no href="/*" or >*</a> in body
- `test_home_renders_card_per_database` — 3 `<article class="card">` elements for 3-db fixture
- `test_home_503_when_datasette_down` — HTTPException 503 raised when /.json returns 500

## Jinja Binding Port Map Applied

| M1 original | Post-port | Reason |
|-------------|-----------|--------|
| `{% extends "default:index.html" %}` | `{% extends "base.html" %}` | Remove datasette prefix |
| `{% block extra_head %}{{ super() }}` | `{% block head %}` | base.html head block is neutral (no super needed) |
| `{% block nav %}{% include "_header.html" %}{% endblock %}` | DELETED | base.html renders nav |
| `databases\|rejectattr('hidden')` | `databases` (handler pre-filters) | Handler removes hidden; template receives clean list |
| `database.table_count` | `database.tables_count` | Actual Datasette /.json field name (M1 had typo) |
| `metadata.databases[database.name]` direct access | `(metadata.databases[database.name] if ... and database.name in metadata.databases else {})` | Avoid KeyError on Starlette strict Jinja |
| `{% block footer %}{% include "_footer.html" %}{% endblock %}` | DELETED | base.html renders footer |

## Architecture Decision: app.state.templates

The plan action specified attaching `templates` to `app.state` so route modules don't import it directly from `main.py`. This pattern prevents a circular import that would otherwise occur when 04-04 adds `routes_database.py` (also needing Jinja rendering) to the same `main.py` import chain.

Route handlers now call `request.app.state.templates.TemplateResponse(...)` — a small indirection that keeps all router modules free of cross-imports.

## Deviations from Plan

None — plan executed exactly as written. All 5 test cases pass with the precise fixture shapes from 04-01.

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `database.size` chip conditional | `templates/index.html:83` | `size` is absent from `/.json` per RESEARCH Assumption A6 — the chip renders when size is present, silently omits when absent. Matches M1 behavior. |

## Threat Register Enforcement

| Threat | Status |
|--------|--------|
| T-04-03-01 XSS (autoescape) | Enforced — Jinja2Templates auto-escapes; `\|safe` only on `s()` developer defaults, never on metadata values |
| T-04-03-02 Wildcard card | Enforced — `_filter_wildcard()` strips `*`; verified by `test_home_filters_wildcard_databases_key` |
| T-04-03-03 Hanging datasette | Enforced — httpx timeout=10s from 04-01; slow upstream surfaced as 503 via HTTPException |
| T-04-03-04 500 stack trace | Enforced — explicit `raise HTTPException(503)` on httpx.HTTPError |
| T-04-03-05 SSTI | Accepted — all template names are developer-controlled literals |
| T-04-03-06 Metadata cache leak | Accepted — public content, process-local |
| T-04-03-07 S3 overlay tampering | Accepted — out of scope Phase 4, IAM-protected |

## Threat Flags

None — no new network endpoints or auth paths introduced. GET / is a public read-only route with no user input.

## Self-Check: PASSED

- `packages/zeeker-frontend/src/zeeker_frontend/routes_home.py` — FOUND
- `packages/zeeker-frontend/src/zeeker_frontend/templates/index.html` — FOUND
- `packages/zeeker-frontend/tests/test_home.py` — FOUND
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` contains `app.include_router(home_router)` — VERIFIED
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` contains `app.state.templates` — VERIFIED
- Commit `896d222` — FOUND
- 32 tests pass, 0 fail

---
phase: 04-port-home-database-pages
plan: "01"
subsystem: zeeker-frontend
tags:
  - m2
  - frontend
  - fastapi
  - jinja2
  - httpx
  - tdd
dependency_graph:
  requires: []
  provides:
    - packages/zeeker-frontend/src/zeeker_frontend/filters.py
    - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/base.html
  affects:
    - packages/zeeker-frontend/pyproject.toml
    - packages/zeeker-frontend/tests/conftest.py
tech_stack:
  added:
    - pytest-httpx==0.36.0 (dev dep)
    - pytest-asyncio==1.3.0 (dev dep)
  patterns:
    - FastAPI lifespan-scoped httpx.AsyncClient
    - Jinja2Templates with custom filters/globals
    - MockTransport-based unit tests (no docker dependency)
    - 60s TTL module-level cache (no cachetools dep)
key_files:
  created:
    - packages/zeeker-frontend/src/zeeker_frontend/filters.py
    - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/base.html
    - packages/zeeker-frontend/tests/test_filters.py
    - packages/zeeker-frontend/tests/test_client.py
    - packages/zeeker-frontend/tests/fixtures/databases.json
    - packages/zeeker-frontend/tests/fixtures/sglawwatch.json
    - packages/zeeker-frontend/tests/fixtures/metadata.json
  modified:
    - packages/zeeker-frontend/pyproject.toml
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
    - packages/zeeker-frontend/tests/conftest.py
decisions:
  - "pytest-httpx upgraded from 0.35.0 to 0.36.0 (0.35 requires pytest==8.*, project uses 9.*)"
  - "Synthetic JSON fixtures created (Docker not running); shapes match datasette /.json, /{db}.json, /-/metadata.json endpoints"
  - "s() implemented as stub returning default — M1 templates always pass literal defaults so 1:1 output preserved"
metrics:
  duration: "~15 minutes"
  completed_date: "2026-04-22"
  tasks_completed: 2
  files_changed: 10
---

# Phase 4 Plan 01: FastAPI Plumbing Scaffold Summary

FastAPI lifespan + Jinja2Templates + M1-ported filters + httpx datasette client with 27 passing unit tests (zero Docker dependency).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add pytest-httpx dev dep + write filters.py + datasette_client.py with unit tests | 2f1ac6a | pyproject.toml, filters.py, datasette_client.py, conftest.py, 3 fixtures, 2 test files |
| 2 | Wire main.py (lifespan + StaticFiles + Jinja2Templates + filters) + write base.html shell | 64c47a6 | main.py, base.html |

## Test Results

- **27 tests passed**, 0 failed, 0 errors
- Test runtime: 0.02s
- Files covered: `filters.py` (22 tests), `datasette_client.py` (5 tests)
- All tests use MockTransport — zero Docker/network dependency

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pytest-httpx version conflict resolved**
- **Found during:** Task 1 (uv sync)
- **Issue:** Plan specified `pytest-httpx==0.35.0` which requires `pytest==8.*`; project uses `pytest==9.0.3`. uv failed with unsatisfiable requirements.
- **Fix:** Upgraded to `pytest-httpx==0.36.0` which is available in local uv cache and explicitly requires `pytest==9.*`.
- **Files modified:** `packages/zeeker-frontend/pyproject.toml`
- **Commit:** 2f1ac6a

**2. Synthetic JSON fixtures (not live-captured)**
- **Found during:** Task 1 (Step 4 fixture capture)
- **Issue:** Docker daemon not running; `curl http://localhost/.json` would fail.
- **Fix:** Created synthetic JSON fixtures with shapes that satisfy all test assertions (`sglawwatch` has `headlines` table; all 3 database names present in `databases.json`).
- **Files:** `tests/fixtures/databases.json`, `tests/fixtures/sglawwatch.json`, `tests/fixtures/metadata.json`
- **Note:** These fixtures should be replaced with live-captured versions when Docker is running. The test suite will continue to pass regardless because it uses MockTransport (not the real fixtures directly via HTTP).

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| REQ-frontend-data-via-http | Met | `datasette_client.py` is pure httpx; `main.py` has no sqlite imports |
| REQ-eliminate-template-drift | Met | `base.html` replaces M1's `_header.html`+`_footer.html` as one shared shell; no `default:` prefix |

## Threat Register Enforcement

| Threat | Status |
|--------|--------|
| T-04-01-01 XSS (autoescape) | Enforced — used `Jinja2Templates(directory=...)` not raw `jinja2.Environment` |
| T-04-01-02 DoS (httpx timeout) | Enforced — `Timeout(10.0, connect=2.0)`, `Limits(max_connections=20)` |
| T-04-01-03 /frontend-test disclosure | Accepted — returns only `{"status":"ok","service":"zeeker-frontend"}` |
| T-04-01-04 s()/plural() tampering | Enforced — s() stub returns developer default only; plural() uses hardcoded dict |
| T-04-01-05 cache poisoning | Accepted — cache key is constant, no user input |
| T-04-01-06 test fixture EoP | Accepted — read-only committed files, test-only dep |
| T-04-01-07 stack trace disclosure | Enforced — no custom debug middleware; FastAPI default 500 JSON response |

## Downstream Consumer Interface

Plans 04-03 and 04-04 consume these exports directly:

```python
# from zeeker_frontend.main import
app: FastAPI                    # app.state.http is the shared httpx.AsyncClient
templates: Jinja2Templates      # 3 filters + 2 globals already registered
DATASETTE_URL: str              # configurable via ZEEKER_DATASETTE_URL env var

# from zeeker_frontend.datasette_client import
fetch_databases(client)         # list[dict] with 'name' key promoted
fetch_database(client, db)      # dict | None (None on 404)
fetch_site_metadata(client)     # dict with 60s TTL cache, {} on error

# Jinja filters (already registered on templates.env):
filesizeformat, pluralize, safe_format, s(), plural()
```

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `s()` returns `default` arg | `filters.py:62` | No strings.yaml in frontend; M1 templates always pass literal defaults so output is 1:1. If Phase 6 needs real i18n, swap in YAML-backed implementation. |

## Self-Check: PASSED

- [x] `packages/zeeker-frontend/src/zeeker_frontend/filters.py` exists
- [x] `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` exists
- [x] `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` exists
- [x] `packages/zeeker-frontend/src/zeeker_frontend/main.py` updated
- [x] Commit `2f1ac6a` exists (Task 1)
- [x] Commit `64c47a6` exists (Task 2)
- [x] 27 tests pass, 0 fail

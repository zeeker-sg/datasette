---
phase: 04-port-home-database-pages
verified: 2026-04-21T23:56:17Z
status: human_needed
score: 11/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Load http://localhost/ in a browser and visually confirm the civic-broadsheet editorial layout — hero, stat band, database cards, footer"
    expected: "Civic-broadsheet home page: large italic-accent H1, petrol stat band with database/table counts, card grid with database cards, four-column footer"
    why_human: "Visual design fidelity (sketch 001-D contract) and footer year rendering cannot be verified programmatically from rendered HTML alone"
  - test: "Load http://localhost/sglawwatch in a browser and visually confirm the editorial-list database overview"
    expected: "Editorial hero with italic last-word H1, petrol stat band, editorial-row table list (.list .row), breadcrumb, no _zeeker_* or FTS tables in list"
    why_human: "Visual design fidelity (sketch 002-B contract) requires a human eye"
  - test: "Confirm footer year is correct (no 2025/2026 mismatch) on both / and /sglawwatch"
    expected: "Footer shows current year (2026), not a stale hardcoded 2025"
    why_human: "REQ-eliminate-template-drift success criterion explicitly lists 'no 2025/2026 footer year mismatch'; requires viewing the live page"
---

# Phase 4: Port Home + Database Pages — Verification Report

**Phase Goal:** Implement frontend routes `/` (homepage with hero, stats, database cards) and `/{db}` (database overview with tables, row counts, schema link, SQL examples). Phase closes on pre-deploy gate green against local dev stack; production deploy deferred by operator.
**Verified:** 2026-04-21T23:56:17Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `/` renders civic-broadsheet home (hero + stat band + card grid) | ✓ VERIFIED | `routes_home.py` handler + `index.html` template: `db-header home-header`, `db-statband`, `<div class="cards">` present. 5 tests pass including `test_home_returns_200_with_card_grid`. Sections B/C of verify_phase_04.sh confirmed green (04-05 SUMMARY). |
| 2 | `/{db}` renders editorial-list database overview | ✓ VERIFIED | `routes_database.py` handler + `database.html` template: `db-header`, `db-statband`, `db-toolbar`, `<div class="list">`, editorial `.row` items. 7 tests pass including `test_database_returns_200_with_editorial_list`. |
| 3 | All tables/views/canned-queries shown; `_zeeker_*` and FTS tables hidden | ✓ VERIFIED | `routes_database.py:33-36` dual filter: `not t.get("hidden") and not t.get("name", "").startswith("_zeeker")`. Fixture `sglawwatch.json` has `_zeeker_updates` with `hidden: false` — the prefix check handles this. `test_database_filters_hidden_zeeker_tables` and `test_database_filters_fts_tables` pass. Views and canned queries passed in context. |
| 4 | HTTP-only data access (no sqlite3 in frontend) | ✓ VERIFIED | `grep -q 'sqlite' main.py/routes_home.py/routes_database.py` all return no match. `test_module_does_not_top_level_import_sqlite3` passes. REQ-frontend-data-via-http satisfied. |
| 5 | 60s TTL metadata cache in datasette_client | ✓ VERIFIED | `datasette_client.py:14` `_METADATA_TTL_SECONDS = 60.0` with `_METADATA_CACHE` dict. `test_fetch_site_metadata_caches` confirms single HTTP call on two consecutive fetches. |
| 6 | Shell chrome (base.html) rendered consistently on both routes | ✓ VERIFIED | `base.html` contains nav (`.db-nav`), conditional breadcrumb (`.db-crumb`), footer (`.site-footer`). Both `index.html` and `database.html` extend `base.html`. `test_database_renders_breadcrumb` confirms breadcrumb renders on `/{db}`. |
| 7 | Self-hosted fonts + local CSS (no CDN) | ✓ VERIFIED | `base.html` references `/static/css/zeeker.css` only. CSS file has 3 `@font-face` rules pointing to `/static/fonts/*.woff2`. No `fonts.googleapis`, `cdnjs`, `jsdelivr`, or `unpkg` references in CSS or templates. All 3 woff2 files present in `static/fonts/`. |
| 8 | Cache-Control header present on GET | ✓ VERIFIED | `routes_home.py:57` and `routes_database.py:71` both set `Cache-Control: public, max-age=60, stale-while-revalidate=300`. `test_home_sets_cache_control` and `test_database_cache_control_header` pass. verify_phase_04.sh section B confirmed green using `curl -D -` workaround (HEAD method returns 405 from uvicorn). |
| 9 | 404 returned for unknown databases (not 500) | ✓ VERIFIED | `routes_database.py:25-27`: `if payload is None: raise HTTPException(status_code=404)`. `fetch_database` returns `None` on upstream 404 (before `raise_for_status`). `test_database_unknown_returns_404` passes. verify_phase_04.sh section D confirmed green. |
| 10 | Phase-5 boundary intact: `/{db}/{table}` still 404 | ✓ VERIFIED | `@router.get("/{db}")` path parameter does not match two-segment paths like `/sglawwatch/headlines`. FastAPI path matcher enforces single-segment. verify_phase_04.sh section F (`/sglawwatch/headlines` → 404) confirmed green. |
| 11 | M1 path `zeeker-base.css` does NOT leak into frontend-served HTML | ✓ VERIFIED | `grep -q 'zeeker-base.css'` returns no match in `base.html`, `index.html`, `database.html`. Tests assert `"zeeker-base.css" not in body`. verify_phase_04.sh section B/C negative assertions confirmed green. |
| 12 | Visual design fidelity matches M1 sketch contracts (001-D home, 002-B database) | ? HUMAN NEEDED | Code produces correct HTML structure and CSS classes. Visual rendering and footer year correctness require human review. |

**Score:** 11/12 truths verified

### Deferred Items

The ROADMAP success criterion "https://data.zeeker.sg/ and https://data.zeeker.sg/{db} render the V2 editorial design from the frontend service" addresses production deployment. Per operator decision, this is deferred to a later milestone action (un-deferring the deploy recipe in `04-05-DEPLOY.md`). Not a gap — intentional deferral.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/zeeker-frontend/src/zeeker_frontend/main.py` | FastAPI app with lifespan, StaticFiles, Jinja2Templates, filters/globals registered | ✓ VERIFIED | Lifespan with `httpx.AsyncClient`, `StaticFiles("/static")`, all filters/globals registered, both routers included |
| `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` | httpx wrapper + 60s TTL cache | ✓ VERIFIED | `fetch_databases`, `fetch_database`, `fetch_site_metadata` + `reset_metadata_cache` present |
| `packages/zeeker-frontend/src/zeeker_frontend/filters.py` | 3 Jinja filters + s/plural helpers | ✓ VERIFIED | 5 functions exported: `filesizeformat`, `pluralize`, `safe_format`, `s`, `plural` |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` | Shared shell chrome with blocks | ✓ VERIFIED | `db-nav`, breadcrumb, `{% block content %}`, `site-footer`, `/static/css/zeeker.css` link |
| `packages/zeeker-frontend/src/zeeker_frontend/routes_home.py` | GET / handler with APIRouter | ✓ VERIFIED | Router with `@router.get("/")`, `_filter_wildcard`, Cache-Control header, 503 on upstream error |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/index.html` | Home page extending base.html | ✓ VERIFIED | `{% extends "base.html" %}`, hero, stat band, card grid; no `default:` prefix, no M1 partials |
| `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py` | GET /{db} handler with APIRouter | ✓ VERIFIED | Router with `@router.get("/{db}")`, dual hidden+prefix filter, 404 on missing db, Cache-Control |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` | Database page extending base.html | ✓ VERIFIED | `{% extends "base.html" %}`, hero, stat band, toolbar, editorial row list, views, canned queries |
| `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` | Harvested CSS ≥700 lines, all shell/home/db classes | ✓ VERIFIED | 1,102 lines; 3 `@font-face`; 167 balanced `{}`; all expected classes present; `va-feed` absent; `.visually-hidden` present |
| `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/inter-latin.woff2` | Self-hosted Inter | ✓ VERIFIED | File exists and non-empty |
| `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/jetbrains-mono-latin.woff2` | Self-hosted JetBrains Mono | ✓ VERIFIED | File exists and non-empty |
| `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/fraunces-latin.woff2` | Self-hosted Fraunces | ✓ VERIFIED | File exists and non-empty |
| `scripts/verify_phase_04.sh` | Phase 4 verifier delegating to Phase 3 | ✓ VERIFIED | Executable; delegates to `verify_phase_03.sh` (section A); adds sections B-G; sections B-F confirmed green per 04-05 SUMMARY |
| `docker-compose.prod.yml` | Production overlay with Caddyfile.prod | ✓ VERIFIED | Minimal overlay; `./Caddyfile.prod:/etc/caddy/Caddyfile:ro` mount |
| `Caddyfile.prod` | Auto-HTTPS for data.zeeker.sg + Phase-3 suffix routing | ✓ VERIFIED | `data.zeeker.sg { ... }` block; `@datasette` matcher identical to dev |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.py` | `filters.py` | `templates.env.filters[...] = zfilters.*` | ✓ WIRED | Lines 74-78: all 3 filters + 2 globals registered |
| `main.py` | `templates/base.html` | `Jinja2Templates(directory=_TEMPLATES_DIR)` | ✓ WIRED | Line 70; `app.state.templates = templates` at line 82 |
| `routes_home.py` | `datasette_client.py` | `fetch_databases`, `fetch_site_metadata` | ✓ WIRED | Import at line 10; called in handler |
| `routes_database.py` | `datasette_client.py` | `fetch_database`, `fetch_site_metadata` | ✓ WIRED | Import at line 10; called in handler |
| `templates/index.html` | `templates/base.html` | `{% extends "base.html" %}` | ✓ WIRED | Line 1 |
| `templates/database.html` | `templates/base.html` | `{% extends "base.html" %}` | ✓ WIRED | Line 1 |
| `templates/base.html` | `static/css/zeeker.css` | `<link rel="stylesheet" href="/static/css/zeeker.css">` | ✓ WIRED | Line 7 |
| `static/css/zeeker.css` | `static/fonts/inter-latin.woff2` | `url('/static/fonts/inter-latin.woff2')` in `@font-face` | ✓ WIRED | Confirmed by grep |
| `docker-compose.prod.yml` | `Caddyfile.prod` | `volumes: ./Caddyfile.prod:/etc/caddy/Caddyfile:ro` | ✓ WIRED | Exact path present |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `templates/index.html` | `databases` | `fetch_databases(client)` → `GET /.json` | Yes — from live datasette API via httpx | ✓ FLOWING |
| `templates/index.html` | `metadata` | `fetch_site_metadata(client)` → `GET /-/metadata.json` | Yes — from live datasette API via httpx | ✓ FLOWING |
| `templates/database.html` | `tables` | `fetch_database(client, db)` → `GET /{db}.json` → `payload["tables"]` filtered | Yes — from live datasette API via httpx | ✓ FLOWING |
| `templates/database.html` | `metadata` | `fetch_site_metadata(client)` → merged into `merged_metadata` dict | Yes — from live datasette API via httpx | ✓ FLOWING |

### Behavioral Spot-Checks

All spot-checks via pytest (MockTransport, no live stack required):

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| GET / returns 200 with cards | `pytest tests/test_home.py` | 5/5 passed | ✓ PASS |
| GET / sets Cache-Control | `pytest tests/test_home.py::test_home_sets_cache_control` | passed | ✓ PASS |
| Wildcard `*` key filtered from home | `pytest tests/test_home.py::test_home_filters_wildcard_databases_key` | passed | ✓ PASS |
| GET /sglawwatch returns 200 with list | `pytest tests/test_database.py::test_database_returns_200_with_editorial_list` | passed | ✓ PASS |
| GET /no-such-db returns 404 | `pytest tests/test_database.py::test_database_unknown_returns_404` | passed | ✓ PASS |
| `_zeeker_*` tables filtered out | `pytest tests/test_database.py::test_database_filters_hidden_zeeker_tables` | passed | ✓ PASS |
| FTS tables filtered out | `pytest tests/test_database.py::test_database_filters_fts_tables` | passed | ✓ PASS |
| Metadata cache 60s TTL | `pytest tests/test_client.py::test_fetch_site_metadata_caches` | passed | ✓ PASS |
| sqlite3 not imported in main | `pytest tests/test_frontend.py::test_module_does_not_top_level_import_sqlite3` | passed | ✓ PASS |
| Full suite | `cd packages/zeeker-frontend && uv run pytest -q` | 41 passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REQ-frontend-route-set | Plans 03, 04, 05 | Frontend serves `/` and `/{db}` | ✓ SATISFIED | `routes_home.py:GET /`, `routes_database.py:GET /{db}` both implemented and tested. Phase 4 covers these two routes; table/row/auxiliary routes are Phase 5-6. |
| REQ-eliminate-template-drift | Plans 01, 02, 03, 04 | Single frontend codebase owns HTML | ✓ SATISFIED | `index.html` + `database.html` extend `base.html`; no M1 `default:` prefix; no `_header.html`/`_footer.html` includes; no `zeeker-base.css` M1 path in any template. ROADMAP success criteria "no 2025/2026 footer year mismatch" requires human verification of live page. |
| REQ-frontend-data-via-http | Plans 01, 03, 04 | No direct SQLite access from frontend | ✓ SATISFIED | All data flows through `httpx.AsyncClient → datasette:8001`. No sqlite imports in any frontend module. Test `test_module_does_not_top_level_import_sqlite3` is a hard gate. |
| REQ-api-byte-parity | Plan 05 (held by Phase 3 Caddy config) | API responses identical pre/post refactor | ✓ SATISFIED (Phase 3 territory) | Phase 4 did not modify datasette routing. verify_phase_04.sh section G delegates to `verify_api_parity.sh` against `phase-03-pre` baseline. 04-05 SUMMARY confirms content drift only (newer data rows), no routing regressions. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `datasette_client.py` | 44-55 | TOCTOU race on `_METADATA_CACHE` — two concurrent coroutines can both bypass expiry guard and double-write | ⚠️ Warning | Benign double-write today (same value, GIL); hazard if second cache field added later. Code Review finding H-01. |
| `filters.py` | 41-49 | `pluralize` comma-form convention inverted from Django/Jinja2 standard (`"plural,singular"` vs standard `"singular,plural"`) | ⚠️ Warning | No active breakage — phase-4 templates use `plural()` not `pluralize()` with commas. Future call sites following the standard convention would produce inverted output silently. Code Review finding M-01. |
| `templates/base.html` | 21 | `menu_links[*].href` rendered without `javascript:` scheme allowlist check | ℹ️ Info | `metadata.json` is operator-controlled config, not user input. Autoescape prevents attribute-break XSS; only a `javascript:` URI via a compromised config file would be a vector. Code Review finding L-01. |
| `templates/index.html` | 17-19, 83-84 | `\|safe` on `s()` return values — works today (stub returns developer-supplied default) but would become injection surface if `s()` is backed by external data | ℹ️ Info | No change needed now; comment-level fix sufficient. Code Review finding L-02. |

No blockers found. The TOCTOU race (H-01) and pluralize convention (M-01) are pre-deploy hardening items, not functionality blockers.

### Human Verification Required

#### 1. Visual design fidelity — home page

**Test:** Load `http://localhost/` in a browser (or `curl http://localhost/ | cat` for quick HTML inspection)
**Expected:** Civic-broadsheet layout matching M1 sketch 001-D: large italic-accent H1 with Fraunces em, petrol stat band with counts, card grid with database cards (one per visible database), four-column footer with correct year (2026)
**Why human:** CSS rendering, font loading, and visual composition require a browser. The ROADMAP success criterion explicitly names "no 2025/2026 footer year mismatch" — this requires reading the rendered year value.

#### 2. Visual design fidelity — database page

**Test:** Load `http://localhost/sglawwatch` in a browser
**Expected:** Editorial-list layout matching M1 sketch 002-B: database hero header with last-word-italic H1, petrol stat band, sticky filter toolbar, editorial row list showing `headlines`, `case_summaries`, `about_singapore_law` (in that order), no `_zeeker_*` or `*_fts*` entries
**Why human:** CSS layout, editorial-row visual formatting, and absence of hidden tables in rendered output require visual confirmation.

#### 3. Footer year correctness (REQ-eliminate-template-drift)

**Test:** Check footer on both pages
**Expected:** Footer shows `© 2026 data.zeeker.sg` — current year, not a hardcoded stale year
**Why human:** `base.html:90` renders `{{ current_year }}` from `datetime.now().year` (passed by both handlers). The template is correct but this ROADMAP success criterion requires visual confirmation.

### Gaps Summary

No gaps blocking goal achievement. All 11 programmatically verifiable must-haves pass. One human verification cluster remains (visual design + footer year correctness per REQ-eliminate-template-drift ROADMAP success criteria). The test suite is fully green at 41 tests; verify_phase_04.sh sections B-F confirmed green against the local dev stack.

**Notable deviation from plan (not a gap):** `routes_database.py` applies a dual filter (`not t.get("hidden") AND not t.get("name", "").startswith("_zeeker")`) rather than the plan's specified single predicate. This was a deliberate live-stack fix (commit `f5fb2f9`) after discovering that `_zeeker_updates` has `hidden: false` in the real fixture — meaning Datasette's `hidden` flag alone was insufficient to exclude all `_zeeker_*` platform tables. The fixture and tests were updated to match. Both the `test_database_filters_hidden_zeeker_tables` and `test_database_filters_fts_tables` tests pass. The code review (finding M-02) flags the test comment as inaccurate but confirms coverage is correct.

---

_Verified: 2026-04-21T23:56:17Z_
_Verifier: Claude (gsd-verifier)_

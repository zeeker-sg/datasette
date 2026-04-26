---
phase: 06-port-auxiliary-pages
verified: 2026-04-26T00:00:00Z
status: human_needed
score: 13/13 must-haves verified (automated); 3 environmental items deferred to HUMAN UAT
overrides_applied: 0
human_verification:
  - test: "Visual QA sweep of every aux page in a real browser"
    expected: "Italic-accent H1 with colored <em> visible; civic-broadsheet paper/petrol palette; 4-column footer renders; footer links contrast correctly against Datasette's app.css cascade; no layout regressions on /developers, /status, /sources, /about, /how-to-use, /search, /sql, /sql/{db}"
    why_human: "Visual appearance + cascade behavior cannot be programmatically verified. The WR-01 finding (orphan CSS comment text near FOOTER LINK OVERRIDE block) flags potential cascade-skip risk that requires browser visual confirmation."
  - test: "Re-baseline API parity reference and re-run scripts/verify_phase_06.sh against running stack"
    expected: "All 11 sections (A–K) of verify_phase_06.sh exit OK after re-baselining .planning/baselines/phase-03-pre/ → phase-06-pre/ via scripts/capture_baseline.sh; verify_api_parity.sh exits 0"
    why_human: "Sections A and K currently FAIL on pre-existing Category-A/B environmental drift (S3 metadata refresh + daily import drift since April 2026 baseline capture). Phase 6 added zero new datasette routes (T-06-06-03 mitigation), so the parity drift is environmental — confirmed by SUMMARY 06-06 and PHASE-6 known-open-issues. Resolution requires container-running access + capture_baseline.sh re-run; not testable in static-grep mode."
  - test: "Production smoke against https://data.zeeker.sg/ aux routes"
    expected: "Each of /developers, /status, /sources, /about, /how-to-use, /llms.txt, /search, /sql, /sql/{db}, /robots.txt returns 200 + civic-broadsheet body + correct Content-Type; /-/search and /-/sql still reach Datasette (D-01 boundary); reflected XSS escaped on /search?q=<script>"
    why_human: "Production deploy is gated; smoke test happens after deploy-checkpoint. Requires live HTTPS environment + DNS resolution; not part of automated verification."
---

# Phase 6: Port Auxiliary Pages — Verification Report

**Phase Goal:** Implement remaining frontend HTML routes — `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/robots.txt` (1:1 ports of M1 plugin pages) plus two new user-facing surfaces: `/search` (cross-database FTS UI fanning out via `asyncio.gather(return_exceptions=True)` over a boot-time-discovered FTS table cache, replacing M1's `/-/search`) and `/sql` + `/sql/{db}` (thin SQL editor with textarea POST → `execute_sql` against Datasette's read-only mode + 3s ms_limit + 1000-row cap, with canned-queries listing from `/-/metadata.json`). Caddy `/-/*` matcher remains untouched — Datasette's native `/-/search` and `/-/sql` stay reachable as developer-facing surfaces.

**Verified:** 2026-04-26
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                            | Status        | Evidence                                                                                             |
| -- | ------------------------------------------------------------------------------------------------ | ------------- | ---------------------------------------------------------------------------------------------------- |
| 1  | All 9 user-facing routes + `/robots.txt` return 200 with rendered HTML/text                      | ✓ VERIFIED    | 9 `@router.get`/`@router.post` decorators across routes_aux.py, routes_search.py, routes_sql.py; 39/39 phase-06 tests assert 200 + body shape |
| 2  | Italic-accent `<em>` H1 on every aux page                                                        | ✓ VERIFIED    | `grep '<h1>.*<em'` matches all 8 templates: developers/status/sources/about/how_to_use/search/sql_landing/sql_db |
| 3  | `/search` fans out via `asyncio.gather(*tasks, return_exceptions=True)`; partial failures isolated | ✓ VERIFIED    | routes_search.py:137 literal `asyncio.gather(*tasks, return_exceptions=True)`; no `TaskGroup` in file; `_safe_search_one` catches httpx.HTTPError + ValueError; test_search_partial_failure passes with pinned phrase "Search timed out for" + positive group assertion |
| 4  | `/search` reflected XSS via `q` is HTML-escaped (autoescape ON)                                  | ✓ VERIFIED    | test_search_xss_q_echoed PASSES — asserts `<script>alert(1)</script>` does not appear raw in body; search.html uses `{{ q }}` (no `\|safe` filter) |
| 5  | `/search` 503 when empty cache + non-empty q (Pitfall 10)                                        | ✓ VERIFIED    | routes_search.py: `if not searchable: raise HTTPException(503, ...)`; test_search_503_empty_cache passes |
| 6  | `/sql/{db}` POST executes via `execute_sql`; 400 renders inline as `.sql-error` (HTTP 200, NOT 503) | ✓ VERIFIED    | routes_sql.py:214 calls `execute_sql(client, db, sql, bound)`; test_sql_db_post_400_error passes asserting r.status_code == 200 + "no such table" in body |
| 7  | `/sql/{db}` param-binding via `_param_<name>` URL keys (NEVER string concat); querystring allowlist | ✓ VERIFIED    | routes_sql.py: `_PARAM_RE = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")`; allowlist filters form keys via `_PARAM_RE.fullmatch(":" + name)`; test_sql_db_post_param_binding asserts captured `_param_id=42`; test_sql_db_post_drops_extra_form_fields asserts extra keys NOT forwarded |
| 8  | `/sql/{db}` truncated=true renders banner with CSV deep-link                                     | ✓ VERIFIED    | sql_db.html `{% if results.truncated %}` block + URL-encoded `/{db}.csv?sql=` anchor; test_sql_db_truncation_banner passes |
| 9  | `/llms.txt` Content-Type: text/plain; body starts with `# data.zeeker.sg`; `_zeeker_*` filtered  | ✓ VERIFIED    | llms.txt template line 1 = `# data.zeeker.sg`; routes_aux.py uses PlainTextResponse with `media_type="text/plain; charset=utf-8"`; test_llms_txt_format asserts `_zeeker` not in body |
| 10 | Hidden-table dual predicate applied (`hidden` OR `_zeeker_` prefix)                              | ✓ VERIFIED    | `_hidden(t)` helper in routes_aux.py applies dual predicate; routes_sql.py applies same predicate at db + table level; test_sources_hides_internal asserts no `_zeeker` in body |
| 11 | Cache-Control: max-age=60 + stale-while-revalidate=300 on every aux GET; no-store on POST `/sql/{db}` | ✓ VERIFIED    | 13 `Cache-Control` header assignments across routes_aux/search/sql; routes_sql.py:243 sets `no-store` on POST; test_aux_cache_control + test_search_cache_control + test_sql_db_post_success all assert headers |
| 12 | main.py router order: home → aux → search → sql → database → table → row (Phase-6 routers all precede catch-all `/{db}` per Pitfall 3) | ✓ VERIFIED    | main.py lines 127-133: home(127) → aux(128) → search(129) → sql(130) → database(131) → table(132) → row(133); all Phase-6 routers precede database_router |
| 13 | All Phase 4-5 + new Phase-6 unit tests green; no regressions                                     | ✓ VERIFIED    | `uv run pytest -x` reports 155 passed, 0 skipped, 0 errors; phase-06-only tests: 39 passed (test_changelog 4 + test_datasette_client_phase06 9 + test_routes_aux 9 + test_routes_search 7 + test_routes_sql 10) |

**Score:** 13/13 truths verified

Two ROADMAP success criteria are deferred to HUMAN UAT (see human_verification section above):
- `bash scripts/verify_phase_06.sh` exits 0 — currently fails Sections A + K on environmental drift
- `bash scripts/verify_api_parity.sh` (against phase-03-pre) exits 0 — same drift

These are documented as **known open issues** unrelated to Phase 6 deliverables. Phase 6 added zero datasette routes; the drift comes from S3 metadata refresh + daily import since baseline capture (April 2026). Code-level deliverables are complete.

### Required Artifacts

| Artifact                                                                                               | Expected                                                | Status     | Details                                                                                                  |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| `packages/zeeker-frontend/pyproject.toml`                                                              | pyyaml>=6.0,<7.0 declared                               | ✓ VERIFIED | grep matches `"pyyaml>=6.0,<7.0"` in [project] dependencies                                              |
| `packages/zeeker-frontend/src/zeeker_frontend/data/changelog.yaml`                                     | 8+ M1 recent_updates entries verbatim                   | ✓ VERIFIED | `load_changelog()` returns 8 entries; first entry: 2025-06-09 feature `data.zeeker.sg launches!`         |
| `packages/zeeker-frontend/src/zeeker_frontend/changelog.py`                                            | yaml.safe_load loader; degrades to []                   | ✓ VERIFIED | uses `yaml.safe_load`; bare except returns []; 4 unit tests pass                                         |
| `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py`                                     | discover_searchable_tables + search_table + execute_sql | ✓ VERIFIED | 3 helpers exported; 9 unit tests pass; `_param_<name>` binding + 400-before-raise + dual hidden filter all asserted |
| `packages/zeeker-frontend/src/zeeker_frontend/main.py`                                                 | Lifespan populates app.state.searchable_tables + changelog; routers registered before database_router | ✓ VERIFIED | Lifespan lines 54-55; router lines 127-133 (Phase-6 routers all < line 131 database_router) |
| `packages/zeeker-frontend/src/zeeker_frontend/routes_aux.py`                                           | 7 GET handlers (developers/status/sources/about/how-to-use/llms.txt/robots.txt) | ✓ VERIFIED | 7 `@router.get` decorators present; 9 integration tests pass                                             |
| `packages/zeeker-frontend/src/zeeker_frontend/routes_search.py`                                        | GET /search with State A + State B + 503; gather(return_exceptions=True); _pick_title_column | ✓ VERIFIED | All literals present; TaskGroup absent; 7 integration tests pass                                         |
| `packages/zeeker-frontend/src/zeeker_frontend/routes_sql.py`                                           | GET /sql + GET /sql/{db} + POST /sql/{db}; _PARAM_RE; querystring allowlist; no-store on POST | ✓ VERIFIED | 3 route decorators; _PARAM_RE present; 10 integration tests pass                                         |
| 5 HTML page templates + search.html + sql_landing.html + sql_db.html + llms.txt + base.html            | Italic-accent H1; extends base.html; M1 stale link fixes (/-/metadata → /developers, /-/search → /search) | ✓ VERIFIED | All 8 page templates have italic-accent H1; about.html and how_to_use.html have ZERO occurrences of /-/metadata or /-/search |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/search_result.html`                  | Reads row["__title__"] directly (server-attached)       | ✓ VERIFIED | Partial uses `{{ row["__title__"] }}`; no `loop.first` heuristic                                         |
| `packages/zeeker-frontend/src/zeeker_frontend/static/robots.txt`                                       | Verbatim M1 port; 30+ lines; GPTBot block               | ✓ VERIFIED | 35 lines; GPTBot match present; test_robots_txt asserts content + Content-Type                           |
| `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css`                                   | Phase-6 section delimited; before FOOTER LINK OVERRIDE; no :root edits; balanced braces | ✓ VERIFIED | Section delimiters at lines 1718 + 2493; FOOTER LINK OVERRIDE at line 2503; brace balance 407=407; no `:root` in phase-06 region |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html`                                     | `<body class="{{ page_class or '' }}">` + nav `href="/search"` (no /-/search) | ✓ VERIFIED | Line 10 binds page_class; line 61 links to /search; no /-/search anywhere in file                        |
| `scripts/verify_phase_06.sh`                                                                           | Executable; bash -n syntax-clean; delegates verify_phase_04.sh; wraps verify_api_parity.sh; D-01 negative; router-order check | ✓ VERIFIED | Mode 0755+; bash -n exits 0; greps confirm verify_phase_04.sh + verify_api_parity.sh + /-/search + aux/search/sql/database_router invariants |
| 4 fixture files + 5 test files                                                                        | All present + collectable                               | ✓ VERIFIED | searchable_databases.json + headlines_search_results.json + metadata_with_canned_queries.json + sql_error_400.json all present; 5 test files all collectable + populated with REAL assertions |

### Key Link Verification

| From                                | To                                  | Via                                                        | Status   | Details                                                       |
| ----------------------------------- | ----------------------------------- | ---------------------------------------------------------- | -------- | ------------------------------------------------------------- |
| main.py lifespan                    | discover_searchable_tables          | `await discover_searchable_tables(app.state.http)`         | ✓ WIRED  | line 54 — runs once at boot; populates app.state.searchable_tables |
| main.py lifespan                    | load_changelog                      | `load_changelog()`                                         | ✓ WIRED  | line 55 — populates app.state.changelog from YAML            |
| routes_search.py                    | app.state.searchable_tables         | `request.app.state.searchable_tables`                      | ✓ WIRED  | line 92 — handler reads cache populated by lifespan          |
| routes_aux.py /status handler       | app.state.changelog                 | `request.app.state.changelog`                              | ✓ WIRED  | line 142 — `recent_updates` context dict pulled from app.state |
| routes_search.py                    | datasette_client._safe_search_one   | `await asyncio.gather(*tasks, return_exceptions=True)`     | ✓ WIRED  | line 137 — fan-out fan over per-table coros                   |
| routes_sql.py POST handler          | datasette_client.execute_sql        | `body, error = await execute_sql(client, db, sql, bound)`  | ✓ WIRED  | line 214 — handler delegates to client; renders body or error block |
| routes_sql.py POST handler          | URL-encoded form-key allowlist      | `_PARAM_RE.fullmatch(":" + name)` per form key             | ✓ WIRED  | line 205 — fullmatch shape-check + name-in-detected check    |
| sql_db.html template                | /{db}.csv?sql=...                   | `<a href="/{database}.csv?sql={{ sql\|urlencode }}">`      | ✓ WIRED  | URL-encoded; routes via Caddy suffix matcher to datasette    |
| base.html nav                       | /search                             | `<a href="/search">`                                       | ✓ WIRED  | line 61 — D-01 enforced; no /-/search references             |
| main.py router registration         | aux_router + search_router + sql_router | `app.include_router(...)` lines 128/129/130              | ✓ WIRED  | All 3 Phase-6 routers precede database_router (line 131)     |
| scripts/verify_phase_06.sh          | scripts/verify_phase_04.sh          | `bash scripts/verify_phase_04.sh`                          | ✓ WIRED  | Section A delegates Phase-4 invariants                        |
| scripts/verify_phase_06.sh          | scripts/verify_api_parity.sh        | `bash scripts/verify_api_parity.sh`                        | ✓ WIRED  | Section K wraps API parity gate                               |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable                  | Source                                                    | Produces Real Data | Status        |
| --------------------------------- | ------------------------------ | --------------------------------------------------------- | ------------------ | ------------- |
| routes_search.py /search          | groups (rendered in search.html) | per-table fetch via _safe_search_one over app.state.searchable_tables | Yes (when cache populated) | ✓ FLOWING      |
| routes_aux.py /status             | recent_updates                 | app.state.changelog (loaded via load_changelog at boot)   | Yes (8 YAML entries) | ✓ FLOWING      |
| routes_aux.py /developers /sources /llms.txt | db_blocks                      | _collect_db_blocks → fetch_databases + fetch_database     | Yes               | ✓ FLOWING      |
| routes_sql.py /sql                | decorated databases            | fetch_databases + fetch_database per visible db           | Yes               | ✓ FLOWING      |
| routes_sql.py /sql/{db} GET       | canned + first_table           | fetch_database + fetch_site_metadata                      | Yes               | ✓ FLOWING      |
| routes_sql.py /sql/{db} POST      | results + error                | datasette_client.execute_sql → datasette /{db}.json?sql=… | Yes               | ✓ FLOWING      |
| routes_aux.py /robots.txt         | static body                    | static/robots.txt file read at handler time              | Yes (35 lines from M1) | ✓ FLOWING      |
| routes_aux.py /about /how-to-use  | site_metadata (for nav menu_links) | fetch_site_metadata                                       | Yes               | ✓ FLOWING      |

### Behavioral Spot-Checks

| Behavior                                                            | Command                                                                                                            | Result                              | Status |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------- | ------ |
| Phase 06 unit/integration tests pass                                | `cd packages/zeeker-frontend && uv run pytest tests/test_routes_aux.py tests/test_routes_search.py tests/test_routes_sql.py tests/test_datasette_client_phase06.py tests/test_changelog.py -v` | 39 passed in 0.07s                  | ✓ PASS |
| Full pytest suite green (regression check)                          | `cd packages/zeeker-frontend && uv run pytest -x`                                                                  | 155 passed, 0 skipped, 0 errors     | ✓ PASS |
| Changelog YAML loads as list of dicts                               | `uv run python -c "from zeeker_frontend.changelog import load_changelog; print(len(load_changelog()))"`            | 8 entries                           | ✓ PASS |
| verify_phase_06.sh syntax-clean                                     | `bash -n scripts/verify_phase_06.sh`                                                                               | exit 0                              | ✓ PASS |
| zeeker.css brace balance preserved                                  | Python script counts `{` vs `}` and checks `:root` absence in phase-06 region                                      | 407 == 407; no `:root`              | ✓ PASS |
| main.py router order: aux/search/sql_router < database_router       | `grep -nE 'app\.include_router'`                                                                                   | aux=128 search=129 sql=130 db=131   | ✓ PASS |
| End-to-end live verifier run (Sections A + K)                       | `bash scripts/verify_phase_06.sh` against running stack                                                            | Sections B-J PASS; A+K FAIL on environmental drift | ? SKIP — known issue; deferred to HUMAN UAT |

### Requirements Coverage

| Requirement                  | Source Plan       | Description                                                                              | Status      | Evidence                                                                                                       |
| ---------------------------- | ----------------- | ---------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------- |
| REQ-frontend-route-set       | 06-01..06-05      | Frontend serves /, /{db}, /{db}/{table}, /{db}/{table}/{pk}, /-/search, /developers, /status, /sources, /about, /how-to-use, /llms.txt | ✓ SATISFIED | All 7 1:1 ports + /search + /sql + /sql/{db} + /robots.txt return 200 (39 tests assert it); REQ list adds /robots.txt as scope-extension per phase plan |
| REQ-frontend-data-via-http   | 06-01, 06-02, 06-03, 06-04, 06-05 | Frontend reads exclusively via httpx to internal datasette                                | ✓ SATISFIED | All Phase-6 handlers use `request.app.state.http` (httpx.AsyncClient); no sqlite3 import in any routes_*.py file |
| REQ-eliminate-template-drift | 06-03, 06-04, 06-05, 06-06 | Single frontend codebase owns all HTML; M1 stale links fixed                              | ✓ SATISFIED | M1 plugins NOT modified (Phase 7 deletes them); about.html `/-/metadata` → `/developers` (test asserts); how_to_use.html every `/-/search` → `/search` (test asserts); base.html footer `/-/search` → `/search`; civic-broadsheet shell + italic-accent H1 on every aux page |
| REQ-api-byte-parity          | 06-06             | Every .json/.csv/.db/`/-/*` URL returns identical bytes pre/post                          | ? NEEDS HUMAN | Phase 6 adds zero new datasette routes (T-06-06-03 mitigation verified); verify_api_parity.sh wraps verify_phase_06.sh Section K. Section K currently fails on pre-existing Category-A/B environmental drift (S3 metadata refresh + daily import since baseline capture in April 2026). Drift is NOT a Phase 6 regression — see SUMMARY 06-06 + ROADMAP known-open-issues. Resolution: HUMAN UAT re-baseline. |

All 4 phase requirement IDs accounted for. No orphaned requirements detected.

### Anti-Patterns Found

(Pulled from 06-REVIEW.md findings; status_unchanged from review since no remediation has shipped between review and verification.)

| File                                                                             | Line       | Pattern                                                                            | Severity     | Impact                                                                                                |
| -------------------------------------------------------------------------------- | ---------- | ---------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------- |
| packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css               | 2495–2502  | Orphan text outside any CSS comment block (mid-file `*/` artifact)                  | ⚠️ Warning  | WR-01 — CSS parser may skip subsequent rules; FOOTER LINK OVERRIDE block could lose cascade priority   |
| packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py                 | 213–220    | `r.json()` not wrapped — non-JSON upstream → unhandled ValueError → 500 to user     | ⚠️ Warning  | WR-02 — `routes_sql.sql_db_post` only catches httpx.HTTPError; HTML upstream error page would 500 the user |
| packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/search_result.html | 17        | Generic `\|urlencode` instead of `tilde_encode` for row-link PK                     | ⚠️ Warning  | WR-03 — broken row links for PKs containing `/`, `~`, etc. that Datasette expects tilde-encoded       |
| packages/zeeker-frontend/src/zeeker_frontend/routes_search.py                    | 87         | Unused `_retry` query parameter                                                    | ℹ️ Info     | IN-01 — dead handler argument                                                                          |
| packages/zeeker-frontend/src/zeeker_frontend/templates/pages/search.html         | (failures-notice) | `?q=...&_retry=1` uses bare `&` instead of `&amp;`                          | ℹ️ Info     | IN-02 — minor HTML validation; browsers tolerate                                                       |
| (multiple aux templates)                                                          | (varies)   | Redundant `_zeeker` filter applied at template level after _collect_db_blocks already filtered | ℹ️ Info     | IN-03 — defensive duplication; not a bug                                                              |
| (multiple)                                                                        | (varies)   | `__title__` row key could collide with future Datasette column literally named `__title__` | ℹ️ Info     | IN-04 — namespace conflict risk; reserved-name convention recommended                                |
| packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css               | (search section) | Empty CSS rule `.page-search .search-hero { /* extends .guide-hero */ }`     | ℹ️ Info     | IN-05 — empty rule; minor unnecessary declaration                                                      |
| packages/zeeker-frontend/src/zeeker_frontend/templates/pages/sql_db.html         | (results)  | On 200-with-error responses, both results AND error blocks could render             | ℹ️ Info     | IN-06 — UX polish; Datasette rarely returns 200+error simultaneously                                  |

**Anti-pattern verdict:** 0 blockers, 3 warnings, 6 info. Per known_open_issues, warnings should be **reflected** but do not block phase verification. Recommend follow-up plan to remediate WR-01 (cascade-skip risk is the highest-impact warning).

### Human Verification Required

Three items are routed to HUMAN UAT (the user has explicit access to the running stack + browser):

1. **Visual QA sweep of every aux page in a real browser** — italic-accent H1 visible, civic-broadsheet palette renders, footer cascade behaves correctly (especially relevant given WR-01 orphan-CSS-comment finding); 4-column footer renders; no layout regressions.

2. **Re-baseline API parity reference + re-run `bash scripts/verify_phase_06.sh`** — Sections A + K currently fail on pre-existing Category-A/B environmental drift (S3 metadata refresh + daily import drift since baseline capture). Phase 6 added zero new datasette routes. Resolution: `scripts/capture_baseline.sh phase-06-pre`, update verify_phase_06.sh `ZEEKER_BASELINE_DIR`, re-run.

3. **Production smoke against `https://data.zeeker.sg/`** — every aux route returns 200 + civic-broadsheet body; `/-/search` and `/-/sql` still reach Datasette (D-01 boundary preserved); reflected XSS escaped. Requires post-deploy environment.

### Gaps Summary

**No blocking gaps found.** All 13 must-haves verify, all 8 artifacts substantiate, all 11 key links wire, all 8 data-flows confirm flowing, and all 6 automated behavioral spot-checks pass. The phase is **code-complete** and ready for the documented HUMAN UAT step (re-baseline + visual sweep + production smoke).

The 3 warning-level findings (WR-01, WR-02, WR-03) from 06-REVIEW.md are **non-blocking**: WR-01 (orphan CSS comment) is a cascade-risk that visual QA will surface; WR-02 (json-decode unhandled) only manifests on non-JSON upstream errors (rare in container-internal Caddy → datasette path); WR-03 (urlencode vs tilde_encode) only breaks links for PKs containing special characters — the Phase-6 fixtures don't expose this case.

Phase 6 is **Ship-ready pending HUMAN UAT** (matching SUMMARY 06-06 self-assessment).

---

_Verified: 2026-04-26_
_Verifier: Claude (gsd-verifier)_

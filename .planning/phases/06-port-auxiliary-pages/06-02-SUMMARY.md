---
phase: 06-port-auxiliary-pages
plan: 02
subsystem: frontend-http-client
tags: [datasette-client, fts-discovery, sql-execution, changelog-loader, lifespan, tdd, wave-1]

requires:
  - phase: 05-port-table-browse-row-view
    provides: "datasette_client.py extension pattern (fetch_table allowlist + 404→None idiom), pytest fixture pattern (_mock helper + httpx.MockTransport)"
  - phase: 06-port-auxiliary-pages-01
    provides: "pyyaml dep declared (6.0.3); data/changelog.yaml with 8 entries; tests/fixtures/{searchable_databases,headlines_search_results,sql_error_400}.json; 13 collectable test stubs in test_datasette_client_phase06.py + test_changelog.py"

provides:
  - "datasette_client.discover_searchable_tables(client) -> dict[str, list[str]] — one-shot FTS probe; filters hidden + _zeeker_* prefix; degrades to {} on httpx error"
  - "datasette_client.search_table(client, db, table, q, size) -> dict | None — wraps /{db}/{table}.json?_search=...&_size=...&_shape=objects"
  - "datasette_client.execute_sql(client, db, sql, params) -> tuple[dict|None, str|None] — wraps /{db}.json?sql=...&_param_*=...&_shape=objects; reads body before raise_for_status() on 400"
  - "zeeker_frontend.changelog.load_changelog() -> list[dict] — yaml.safe_load with bare-except boot tolerance"
  - "main.py lifespan extension populating app.state.searchable_tables + app.state.changelog (Plans 03-05 read these without re-querying datasette)"

affects: ["06-03-PLAN", "06-04-PLAN", "06-05-PLAN"]

tech-stack:
  added: []
  patterns:
    - "TDD per task (RED test commit + GREEN implementation commit) — 4 commits across 3 tasks"
    - "Lifespan-cached probes (D-04, D-12) — one-shot at boot, cached for process lifetime; daily container restart = natural cache invalidation"
    - "Body-before-raise_for_status idiom for 400 (Pitfall 1) — preserves Datasette's friendly SQL error string"
    - "Explicit allowlist param construction in execute_sql (only sql + _shape + _param_<name>) — never params=request.form() (threat T-06-02-01)"

key-files:
  created:
    - "packages/zeeker-frontend/src/zeeker_frontend/changelog.py"
  modified:
    - "packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py (+107 lines: 3 new helpers appended after fetch_row)"
    - "packages/zeeker-frontend/src/zeeker_frontend/main.py (+10 lines: 2 imports + 2 app.state populate calls inside lifespan)"
    - "packages/zeeker-frontend/tests/test_datasette_client_phase06.py (replaced 9 pytest.skip stubs with real assertions, +193 net)"
    - "packages/zeeker-frontend/tests/test_changelog.py (replaced 4 pytest.skip stubs with real assertions, +26 net)"

key-decisions:
  - "Used asyncio.gather-style explicit per-db iteration in discover_searchable_tables rather than parallelising fetch_database calls — only runs once at boot, simplicity > 2-3ms wall-clock saving."
  - "execute_sql returns (body, error) tuple unconditionally (never raises on body.error populated on 200) — gives /sql/{db} handler a uniform two-branch render path. RESEARCH §Pattern 4 confirms this is the simplest contract."
  - "Bare except Exception in load_changelog (intentional, RESEARCH-recommended) — lifespan must boot even if a malformed YAML edit lands on disk; /status degrades to 'No updates yet' rather than crashing the entire app."
  - "Lifespan smoke-test required FastAPI lifespan-context manual invocation (httpx.ASGITransport in 0.28+ does NOT auto-run lifespan). Verified app.state.searchable_tables = {} and app.state.changelog len = 8 with no real datasette upstream — boot tolerance works."

requirements-completed: [REQ-frontend-data-via-http, REQ-frontend-route-set]

duration: ~4 min
completed: 2026-04-26
---

# Phase 6 Plan 02: Wave-1 Helpers + Lifespan Summary

**Three datasette_client helpers (`discover_searchable_tables`, `search_table`, `execute_sql`) appended to the existing module, a new `changelog.py` YAML loader, and a 2-line lifespan extension wiring both into `app.state` — 13 unit tests pass with 0 skips and the full Phase 4-5 suite stays green.**

## Performance

- **Duration:** ~4 min (start 01:40:19Z, end 01:44:02Z UTC)
- **Started:** 2026-04-26T01:40:19Z
- **Completed:** 2026-04-26T01:44:02Z
- **Tasks:** 3 (all TDD with explicit RED → GREEN per task; Tasks 1+2 each shipped as 2 commits)
- **Files modified:** 5 (1 created, 4 modified)
- **Tests added:** 13 real (replacing 13 pytest.skip stubs from Plan 01); full suite now 129 passed, 19 skipped (remaining stubs belong to Plans 03-05).

## Accomplishments

### Final signatures (datasette_client.py)

```python
async def discover_searchable_tables(
    client: httpx.AsyncClient,
) -> dict[str, list[str]]:
    """Return {db_name: [table_names_with_fts]}. Filters hidden + _zeeker_*."""

async def search_table(
    client: httpx.AsyncClient,
    db: str,
    table: str,
    q: str,
    size: int = 10,
) -> dict | None:
    """GET /{db}/{table}.json?_search=q&_size=size&_shape=objects. None on 404."""

async def execute_sql(
    client: httpx.AsyncClient,
    db: str,
    sql: str,
    params: dict[str, Any] | None = None,
) -> tuple[dict | None, str | None]:
    """Returns (body, error). 400 → (None, body.error); 404 → (None, 'Database not found')."""
```

### Critical invariants verified by tests

- `_shape=objects` is **always** set on `search_table` and `execute_sql` requests, regardless of caller-supplied params (`test_search_table_passes_q_and_size`, `test_execute_sql_shape_objects_always_set`).
- `execute_sql` binds params via `_param_<name>=value` URL keys; the SQL string is **never** mutated by caller-supplied values (`test_execute_sql_builds_param_url`). This closes the SSRF-via-querystring-smuggling surface (threat T-06-02-01).
- `execute_sql` reads the response body **before** `raise_for_status()` on HTTP 400, so Datasette's `body.error` string ("no such table: nope") survives intact (`test_execute_sql_400_returns_friendly_error`). This satisfies threat T-06-02-03.
- `discover_searchable_tables` filters BOTH `hidden=True` (covers `*_fts` internal tables) AND `name.startswith("_zeeker")` (covers platform tables that may have `hidden=False` in some overlays). Both predicates are mandatory (`test_discover_searchable_filters_hidden`, `test_discover_searchable_filters_zeeker_prefix`). This satisfies threat T-06-02-02.
- `discover_searchable_tables` only includes tables whose `fts_table` field is truthy (string). Tables with `fts_table: None` are silently dropped (`test_discover_searchable_extracts_fts_table` includes a `categories` table with `fts_table=None` that does NOT appear in the output dict).

### `changelog.py` module structure

```
src/zeeker_frontend/
├── changelog.py            # NEW — load_changelog() + _DATA_DIR module constant
└── data/
    └── changelog.yaml      # from Plan 01 — 8 entries (2 M1 verbatim + 6 phase milestones)
```

The module-level `_DATA_DIR = Path(__file__).parent / "data"` constant is exposed so tests can `monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)` to swap in a synthetic YAML per test (no global filesystem state mutation between tests).

`yaml.safe_load` is used exclusively (threat T-06-02-05). The bare `except Exception` is intentional: lifespan boot must survive a malformed YAML edit landing on disk — the page degrades to "No updates yet" rather than crashing the whole app.

### `main.py` lifespan diff

```python
+ from zeeker_frontend.changelog import load_changelog
+ from zeeker_frontend.datasette_client import discover_searchable_tables
  ...
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      app.state.http = httpx.AsyncClient(...)
+     # Phase 6 (D-04, D-12) — one-shot probes at boot, cached for the
+     # process lifetime. Both helpers degrade to empty containers on
+     # failure (RESEARCH Pitfall 10) so the lifespan never crashes when
+     # datasette is briefly unavailable at start-up.
+     app.state.searchable_tables = await discover_searchable_tables(app.state.http)
+     app.state.changelog = load_changelog()
      try:
          yield
      finally:
          await app.state.http.aclose()
```

Two imports + two assignment lines + one comment block. The new lines run AFTER `app.state.http` is constructed (so the helpers can use it) and BEFORE `try: yield` (so the populate is complete before the first request lands).

### Smoke-test result (lifespan boot tolerance)

Manually drove the lifespan against the actual app with no real datasette upstream:

```
status: 200
searchable_tables: {}        # boot tolerance kicked in (Pitfall 10)
changelog len: 8             # real YAML loaded from disk
```

`searchable_tables == {}` confirms `discover_searchable_tables` swallows the connection error (no datasette container is running on this host) and returns `{}` — Plan 04's `/search` route will render a 503 friendly when this dict is empty AND `q` is non-empty (Pitfall 10), but State A (empty `q`) still renders.

`changelog len == 8` confirms `load_changelog` reads the real `data/changelog.yaml` from Plan 01 and returns the 8-entry list.

## Task Commits

1. **Task 1 RED:** test(06-02): add failing tests for Phase 6 datasette_client helpers — `c9dec09`
2. **Task 1 GREEN:** feat(06-02): add discover_searchable_tables / search_table / execute_sql — `d7ed1a9`
3. **Task 2 RED:** test(06-02): add failing tests for changelog YAML loader — `7b03538`
4. **Task 2 GREEN:** feat(06-02): add load_changelog YAML loader module — `82436e5`
5. **Task 3:** feat(06-02): wire lifespan to populate searchable_tables + changelog — `5296a21`

**Plan metadata:** (this commit, batched with STATE.md + ROADMAP.md updates)

## Files Created/Modified

### Created
- `packages/zeeker-frontend/src/zeeker_frontend/changelog.py` — load_changelog YAML loader (40 lines)

### Modified
- `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` — appended 3 new helpers after fetch_row (+107 lines)
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` — 2 imports + 2 lifespan populate calls (+8 lines)
- `packages/zeeker-frontend/tests/test_datasette_client_phase06.py` — replaced 9 pytest.skip stubs with real assertions
- `packages/zeeker-frontend/tests/test_changelog.py` — replaced 4 pytest.skip stubs with real assertions

## Decisions Made

- **One-shot per-db iteration in discover_searchable_tables** — boot-time only; the wall-clock saving from parallelising the per-database `fetch_database` calls (~2-3ms with current 3 databases) is not worth the added complexity. Sequential iteration is verified correct by `test_discover_searchable_extracts_fts_table` covering 2 databases.
- **execute_sql tuple contract — never raises on body.error** — returns `(body, body.error)` even when the 200 response carries a populated `error` field. Gives the future `/sql/{db}` POST handler a single uniform render path (test for `error` truthy → render error block; otherwise render results). RESEARCH §Pattern 4 confirms this is the simplest API.
- **Bare except in load_changelog** — RESEARCH-recommended (D-12 boot-tolerance + threat T-06-02-05 mitigation). The defensive scope is intentional: any YAML parse error, type error, or filesystem oddity returns `[]` so lifespan boots and `/status` shows "No updates yet".
- **Lifespan smoke required manual context invocation** — discovered during Task 3 verification: httpx 0.28.1's `ASGITransport` does NOT auto-run lifespan. Smoke now wraps the test in `async with lifespan(app):` to drive boot. This is verification-only (does not affect production deploy where uvicorn manages lifespan natively).

## Deviations from Plan

### Auto-fixed issues

None — plan executed exactly as written. The only minor friction was the smoke-test command in Task 3's `<action>` Step 3, which constructed a `httpx.AsyncClient(transport=httpx.ASGITransport(app=app))` directly and printed `searchable_tables: MISSING` because lifespan didn't run. Wrapped in `async with lifespan(app):` for the verification call; this is a smoke-test-only adjustment with no production impact (uvicorn drives lifespan natively in real deploys).

The pyproject.toml `pyyaml>=6.0,<7.0` line was already declared by Plan 01 — `import yaml` works in the venv with no further changes.

## Issues Encountered

None functionally blocking. Note for future plans: when smoke-testing FastAPI lifespan via httpx.AsyncClient + ASGITransport, wrap the test in `async with lifespan(app):` because httpx 0.28+ does not auto-run lifespan.

## User Setup Required

None.

## Threat Flags

None new. The plan's `<threat_model>` enumerates T-06-02-01..05; all five are mitigated by this plan's deliverables:

- T-06-02-01 (SSRF via querystring smuggling) → mitigated by explicit `ds_params` dict construction in `execute_sql` (only `sql`, `_shape=objects`, `_param_<name>` keys; tested via `test_execute_sql_builds_param_url`).
- T-06-02-02 (FTS discovery leaks _zeeker / hidden tables) → mitigated by both predicates in `discover_searchable_tables`; tested via `test_discover_searchable_filters_zeeker_prefix` + `test_discover_searchable_filters_hidden`.
- T-06-02-03 (raise_for_status before reading body loses Datasette's 400 message) → mitigated by 400 check before raise_for_status; tested via `test_execute_sql_400_returns_friendly_error`.
- T-06-02-04 (empty FTS-discovery cache after boot blip) → mitigated by `discover_searchable_tables` returning `{}` on httpx error; verified by smoke test (no real datasette → `searchable_tables == {}`). Plan 04's `/search` will raise 503 on empty cache + non-empty `q`.
- T-06-02-05 (yaml.load arbitrary object instantiation) → mitigated by `yaml.safe_load` ONLY in `load_changelog`; verified by `grep yaml.load(` returning no matches.

## Self-Check: PASSED

- `packages/zeeker-frontend/src/zeeker_frontend/changelog.py` → FOUND (40 lines)
- `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` → FOUND with `discover_searchable_tables` + `search_table` + `execute_sql` (3 grep matches)
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` → FOUND with `app.state.searchable_tables = await discover_searchable_tables` AND `app.state.changelog = load_changelog()`
- `packages/zeeker-frontend/tests/test_datasette_client_phase06.py` → 9/9 real tests, 0 skips
- `packages/zeeker-frontend/tests/test_changelog.py` → 4/4 real tests, 0 skips
- Commit `c9dec09` (Task 1 RED) → FOUND in `git log`
- Commit `d7ed1a9` (Task 1 GREEN) → FOUND in `git log`
- Commit `7b03538` (Task 2 RED) → FOUND in `git log`
- Commit `82436e5` (Task 2 GREEN) → FOUND in `git log`
- Commit `5296a21` (Task 3) → FOUND in `git log`
- Full suite `uv run pytest` → 129 passed, 19 skipped (Plans 03-05 stubs), 0 errors, 0 failures
- Smoke `python -c "from zeeker_frontend.changelog import load_changelog; print(len(load_changelog()))"` → 8

## TDD Gate Compliance

Tasks 1 + 2 each have a `test(...)` commit IMMEDIATELY followed by a `feat(...)` commit. Task 3 is `tdd="false"` in the plan and is committed as a single `feat(...)` commit (no test file changes).

- Task 1: `c9dec09` (test) → `d7ed1a9` (feat) ✓
- Task 2: `7b03538` (test) → `82436e5` (feat) ✓
- Task 3: `5296a21` (feat, lifespan extension; no new tests required — full suite serves as regression gate) ✓

## Next Plan Readiness

Plans 06-03 (auxiliary handlers), 06-04 (`/search`), and 06-05 (`/sql`) can now read from `app.state.searchable_tables` and `app.state.changelog` without re-querying datasette per request:

- **Plan 06-03 (`routes_aux.py`)** — `/status` reads `request.app.state.changelog` (8 entries currently); `/sources`, `/developers`, `/llms.txt` use the existing `fetch_databases` + `fetch_database` helpers; no new datasette_client work needed.
- **Plan 06-04 (`routes_search.py`)** — fan-out across `request.app.state.searchable_tables` using `search_table` per (db, table) pair. The boot-tolerance contract (`searchable_tables == {}` → 503 on non-empty `q`) is locked in.
- **Plan 06-05 (`routes_sql.py`)** — POST handler calls `execute_sql(client, db, sql, params)` and renders the `(body, error)` tuple uniformly.

---
*Phase: 06-port-auxiliary-pages*
*Completed: 2026-04-26*

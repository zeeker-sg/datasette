# Phase 7 deferred items

Items found during Phase 7 plan execution that are out-of-scope for the current
plan and DO NOT block ship. Tracked here for triage at HUMAN-UAT close-out.

---

## Plan 07-02 (Wave-1)

### 1. verify_phase_03.sh §F.1 uppercase-.JSON case-insensitivity test fails

- **Found during:** Plan 07-02 Task 3 smoke pass (`bash scripts/verify_phase_06.sh`).
- **Symptom:** Section F.1 of verify_phase_03.sh (chained from verify_phase_06)
  reports `FAIL  uppercase .JSON may have fallen through (body: <!DOCTYPE html>...)`.
- **Root cause:** Caddyfile uses `path *.json` matcher which is case-sensitive
  by default; `/SGLAWWATCH.JSON` falls through to the frontend's 404 page
  (which renders as HTML, not JSON-with-`tables`-key). The verifier comment
  on line 237 of verify_phase_03.sh asserts "Caddy path matcher is
  case-insensitive" — this is **incorrect** per the Caddy docs (matchers are
  case-sensitive unless `path_regexp` with `(?i)` is used).
- **Pre-existing:** YES — not introduced by this plan. Plan 07-01's smoke
  pass was opt-skipped because the local stack was not running. The Phase-6
  SUMMARY reports "all 11 sections green" but that run may have used
  different baseline conditions or the test was tolerated upstream.
- **Why deferred:** Plan 07-02's scope is metadata.json edit + baseline
  re-capture + cascade prepend. Fixing the Caddy case-matcher (or adjusting
  the verifier's assertion to accept a 404 from the frontend on uppercase
  .JSON) is a Caddy-config / verifier-fingerprint concern outside this
  plan's frontmatter (`files_modified` lists metadata.json + baselines +
  3 verifier-cascade lines, NOT verify_phase_03.sh §F).
- **Triage path:** Either (a) add `(?i)` case-insensitive matching to the
  Caddy path matcher (architectural decision — affects every path), OR
  (b) update verify_phase_03.sh §F.1 to accept a 404-from-frontend body as
  valid (acknowledges the production semantic: uppercase data-API URLs
  are not supported). Recommend (b) as the minimum-surface fix.
- **Owner:** Phase 7 HUMAN-UAT close-out OR Plan 07-05 deploy gate.

---

## Plan 07-04 (Wave-2)

### 2. Pre-existing root pytest collection failures (`No module named 'scripts'`)

- **Found during:** Plan 07-04 Task 5 verification (`uv run pytest tests/ -q`).
- **Symptom:** `tests/test_download_from_s3.py` and `tests/test_manage.py`
  fail collection with `ModuleNotFoundError: No module named 'scripts'`. Both
  test modules `import` from `scripts.download_from_s3` / `scripts.manage`,
  but the project's `pyproject.toml` does not configure a `[tool.pytest.ini_options]`
  block with `pythonpath = ["."]` or similar, and no `conftest.py` adds the
  project root to `sys.path`.
- **Pre-existing:** YES — verified via `git stash --keep-index` of Plan 07-04
  fixture edits and re-running pytest on the un-edited working tree. Same
  collection failures with identical error messages. NOT introduced by Plan
  07-04's edits to `tests/conftest.py` + `tests/fixtures.py`.
- **Why deferred:** Plan 07-04's `files_modified` does not include
  `pyproject.toml` (the natural location for pytest path config). Fixing the
  PYTHONPATH issue is a test-infrastructure concern that should land as a
  standalone commit, not be bundled into the mass-delete plan.
- **Triage path:** Add to `pyproject.toml` under `[tool.pytest.ini_options]`:
  `pythonpath = ["."]`. Alternatively, add a top-level `conftest.py` that
  adjusts `sys.path`. The former is preferred (declarative, no Python code).
- **Owner:** Phase 8 OR Phase 7 HUMAN-UAT close-out.

### 3. Pre-existing `test_cache_headers.py` runtime failures (pytest-asyncio not in auto mode)

- **Found during:** Plan 07-04 Task 5 + Task 6 verification.
- **Symptom:** All 7 tests in `tests/test_cache_headers.py` fail with
  `Failed: async def functions are not natively supported. ...` and pytest
  warnings `PytestUnknownMarkWarning: Unknown pytest.mark.asyncio - is this
  a typo?`. The tests use `@pytest.mark.asyncio` + `async def` (the standard
  pytest-asyncio idiom), but `pytest-asyncio` is not in `pyproject.toml`'s
  `[dependency-groups.dev]` list AND the `asyncio_mode = "auto"` config is
  not set.
- **Pre-existing:** YES — verified via the same stash-and-rerun proof as
  item #2. The failures predate Plan 07-04. The test file itself has not
  been modified by any Phase-7 plan.
- **Why deferred:** Plan 07-04's scope is mass-delete + Dockerfile narrowing
  + entrypoint fix + fixture scrub. Adding `pytest-asyncio` to the dev
  dependency group + adjusting pyproject.toml is a test-infrastructure
  concern outside this plan's frontmatter.
- **Triage path:** Add `pytest-asyncio>=0.23.0` to the `[dependency-groups.dev]`
  block in `pyproject.toml`, then add `[tool.pytest.ini_options]` with
  `asyncio_mode = "auto"`. Re-run `uv sync --group dev`; verify
  `uv run pytest tests/test_cache_headers.py` exits 0.
- **Owner:** Phase 8 OR Phase 7 HUMAN-UAT close-out.

### 4. `docker-compose.no-s3.yml` override file is now obsolete (Plan 07-03 + 07-04 shipped)

- **Found during:** Plan 07-04 Gate-1 verification.
- **Symptom:** The local-only `docker-compose.no-s3.yml` override (created
  by Plan 07-02 to bypass the S3 sync during baseline capture, gitignored)
  is no longer needed for runtime — Plan 07-03 disabled the in-script S3
  sync at the source. However, the override is still useful for **gate
  verification of post-prune images** (Plan 07-04's Gate 1 used it to test
  the rebuilt image without modifying production S3).
- **Pre-existing:** Created by Plan 07-02 as a temporary workaround.
- **Why deferred:** Cleanup vs retention is a judgment call. RECOMMEND
  RETAIN: the override is a useful pattern for any future plan that needs
  to gate-verify a baked-in image against snapshot data without touching
  production S3. Document the pattern in PROJECT.md or a notes file.
- **Triage path:** Either (a) delete `docker-compose.no-s3.yml` after Plan
  07-05 ships (Phase-7 close-out), OR (b) document the pattern in
  `.planning/notes/` and keep the gitignored file for reuse. Recommend (b).
- **Owner:** Phase 7 HUMAN-UAT close-out OR Phase 8.

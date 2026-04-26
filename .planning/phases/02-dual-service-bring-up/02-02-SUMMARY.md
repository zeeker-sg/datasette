---
phase: 02-dual-service-bring-up
plan: 02
subsystem: infra
tags: [fastapi, uv, docker, jinja2, httpx, frontend-scaffold]

requires:
  - phase: 02-dual-service-bring-up
    provides: Wave-0 verifier scripts (Plan 02-01) — `verify_phase_02.sh` will exec into the frontend container and grep for the no-sqlite fence this plan establishes
provides:
  - packages/zeeker-frontend/ — uv-managed FastAPI package (placeholder service)
  - Buildable Docker image (python:3.12-slim + uv, ~389MB) with no sqlite3 binary
  - Pinned dependency lockfile (uv.lock) for deterministic Phase 4–6 builds
  - Test scaffolding (pytest 9.x + TestClient) for future HTML route work
  - Architectural fence: no sqlite/datasette deps in pyproject.toml or uv.lock; no apt-get in Dockerfile
affects: [02-04 docker-compose mutation (will reference build.context = ./packages/zeeker-frontend), 02-05 verify (will assert no sqlite3 in container), Phases 4–6 (will fill src/zeeker_frontend/templates and routes)]

tech-stack:
  added:
    - "fastapi[standard]==0.136.0"
    - "httpx==0.28.1"
    - "jinja2==3.1.6"
    - "uvicorn[standard]==0.44.0"
    - "pytest==9.0.3 (dev)"
    - "black==26.3.1 (dev)"
    - "ruff==0.15.11 (dev)"
    - "hatchling (build backend)"
  patterns:
    - "uv-from-ghcr Docker pattern: COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/ — avoids apt-get for the uv binary"
    - "Two-stage uv sync: deps first (--no-install-project) for layer caching, then project install"
    - "Architectural-fence-as-test: test_module_does_not_top_level_import_sqlite3 codifies DEC-5 in pytest"

key-files:
  created:
    - packages/zeeker-frontend/pyproject.toml
    - packages/zeeker-frontend/uv.lock
    - packages/zeeker-frontend/README.md
    - packages/zeeker-frontend/.dockerignore
    - packages/zeeker-frontend/Dockerfile
    - packages/zeeker-frontend/src/zeeker_frontend/__init__.py
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
    - packages/zeeker-frontend/src/zeeker_frontend/templates/.gitkeep
    - packages/zeeker-frontend/src/zeeker_frontend/static/.gitkeep
    - packages/zeeker-frontend/tests/__init__.py
    - packages/zeeker-frontend/tests/conftest.py
    - packages/zeeker-frontend/tests/test_frontend.py
  modified: []

key-decisions:
  - "Frontend gets its own pyproject.toml + uv.lock under packages/zeeker-frontend/; existing flat datasette layout left untouched (defer rename to Phase 7 per CONTEXT option-b)"
  - "README.md must be COPY'd into the Docker build alongside src/ because pyproject.toml's `readme = \"README.md\"` field forces hatchling to read it during the wheel build"
  - "No-sqlite fence enforced at THREE layers: (1) pyproject.toml deps, (2) uv.lock, (3) container image binary absence — all three asserted in acceptance criteria"
  - "uv.lock generated on the host and committed BEFORE the first docker build, so Dockerfile can use `uv sync --frozen` (RESEARCH Pitfall 8)"

patterns-established:
  - "Frontend-package layout: pyproject.toml + src/<pkg>/ + tests/ + Dockerfile + .dockerignore + README at packages/zeeker-frontend/ — template for any future M2 sub-package"
  - "uv-managed FastAPI + slim Docker recipe: pin hatchling as build backend, two-stage uv sync, uvicorn direct invocation (no gunicorn wrapper), no system packages installed"
  - "Forward-compat smoke test: tests/test_frontend.py asserts unknown paths return 404 (not catch-all 200) so Phase 3's suffix-routing assumption holds"

requirements-completed:
  - REQ-frontend-data-via-http
  - REQ-incremental-migration

duration: ~4min
completed: 2026-04-20
---

# Plan 02-02: Frontend Package Scaffold Summary

**uv-managed FastAPI placeholder package at packages/zeeker-frontend/ with /frontend-test route, 3 passing pytest smoke tests, and a 389MB python:3.12-slim Docker image that contains zero sqlite3 surface (binary, deps, or imports).**

## Performance

- **Duration:** ~4 minutes (executor wall time, including Docker build)
- **Started:** 2026-04-20T23:49:29Z
- **Completed:** 2026-04-20T23:52:55Z
- **Tasks:** 2 (both autonomous)
- **Files created:** 12 (11 in Task 1 + 1 Dockerfile in Task 2)
- **Files modified:** 0

## Accomplishments

- `packages/zeeker-frontend/` stood up as a uv-managed FastAPI package; `uv lock` resolved 54 packages cleanly and `uv sync` installed them.
- `GET /frontend-test` returns `{"status":"ok","service":"zeeker-frontend"}` with HTTP 200 — verified via both pytest TestClient and a live `docker run` smoke test on host port 18000.
- All 3 pytest smoke tests green: 200+body match, unknown path → 404 (catch-all guard), and the package-fence test confirming `zeeker_frontend.main` does not contain the string `sqlite3`.
- Dockerfile builds cleanly using `uv` from the official `ghcr.io/astral-sh/uv:latest` image — no apt-get, no curl, no wget, no libsqlite. Image weighs 389MB.
- `docker run --rm --entrypoint sh zeeker-frontend:phase-02-test -c '! command -v sqlite3'` exits 0 — proving the image fence holds at runtime, not just at dependency-declaration time.
- `templates/.gitkeep` and `static/.gitkeep` scaffolded so Phases 4–6 have a place to land HTML/CSS without restructuring.

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold packages/zeeker-frontend/ files + generate uv.lock** — `b536f64` (feat)
2. **Task 2: Add frontend Dockerfile + verify image build / no-sqlite fence** — `7deab3f` (feat)

**Plan metadata:** _(committed below alongside SUMMARY.md, STATE.md, ROADMAP.md, REQUIREMENTS.md)_

## Files Created/Modified

- `packages/zeeker-frontend/pyproject.toml` — Project metadata; pins fastapi[standard]==0.136.0, httpx==0.28.1, jinja2==3.1.6, uvicorn[standard]==0.44.0; dev deps pytest/black/ruff; hatchling build backend; black+ruff line-length 100 / target py312
- `packages/zeeker-frontend/uv.lock` — 54-package deterministic lockfile (192KB); zero sqlite/datasette package entries
- `packages/zeeker-frontend/README.md` — One-paragraph placeholder + local dev recipe; explicitly documents the no-sqlite/no-./data discipline
- `packages/zeeker-frontend/.dockerignore` — Excludes .venv, __pycache__, .pytest_cache, .ruff_cache, *.egg-info, tests/, .git, .gitignore, .dockerignore, Dockerfile from build context
- `packages/zeeker-frontend/Dockerfile` — python:3.12-slim base; uv from ghcr.io/astral-sh/uv:latest; two-stage `uv sync --frozen --no-cache` (deps then project); EXPOSE 8000; CMD `uv run uvicorn zeeker_frontend.main:app --host 0.0.0.0 --port 8000`
- `packages/zeeker-frontend/src/zeeker_frontend/__init__.py` — Package docstring + `__version__ = "0.1.0"`
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` — FastAPI app with `GET /frontend-test` route; no sqlite import (asserted by test)
- `packages/zeeker-frontend/src/zeeker_frontend/templates/.gitkeep` — Empty scaffold for Phases 4–6
- `packages/zeeker-frontend/src/zeeker_frontend/static/.gitkeep` — Empty scaffold for Phases 4–6
- `packages/zeeker-frontend/tests/__init__.py` — Empty package marker
- `packages/zeeker-frontend/tests/conftest.py` — `client` fixture wrapping FastAPI TestClient bound to the placeholder app
- `packages/zeeker-frontend/tests/test_frontend.py` — 3 tests: 200+body, unknown-404, sqlite3 fence (string-in-source assertion)

## Pinned Versions vs Resolved Versions

All four runtime deps pinned exactly in pyproject.toml resolved without drift in uv.lock:
- `fastapi[standard]==0.136.0` → resolved 0.136.0
- `httpx==0.28.1` → resolved 0.28.1
- `jinja2==3.1.6` → resolved 0.28.1's transitive deps unaffected; jinja2 resolved 3.1.6
- `uvicorn[standard]==0.44.0` → resolved 0.44.0

Dev deps (`black==26.3.1`, `pytest==9.0.3`, `ruff==0.15.11`) likewise resolved at the pinned versions. No `==` constraint required relaxation. `uv.lock` is committed.

## Image Stats

- Tag (test-only, removed after verification): `zeeker-frontend:phase-02-test`
- Size: **389MB** (python:3.12-slim ~120MB + uv binary + 54 wheels + project src)
- Manifest sha256: `bc20177c139aa2afe65747fae191712e7cbd0dea9ed7151e9f7d3cb3f66118d0`
- Test image deleted after verification per plan cleanup directive; Plan 02-04 will rebuild via compose

## Decisions Made

- **Pin `==` strictly for all four runtime deps** — pyproject.toml uses `==` rather than `>=` because RESEARCH explicitly verified the version set as a working combination on 2026-04-20. Future bumps go via `uv lock --upgrade-package <name>` + a planned bump commit, not silent floor drift.
- **README.md is part of the build, not just the docs surface** — discovered during Docker build (Task 2). hatchling reads `pyproject.toml` `readme = "README.md"` at wheel build time and refuses to build if the file is missing from the WORKDIR. Fix was a one-line `COPY README.md ./README.md` between the source copy and the second `uv sync`.
- **Two `uv sync` invocations, not one** — first invocation uses `--no-install-project` to install deps only (cacheable layer); second invocation (after src/ is copied) installs the project itself. Standard astral pattern; halves layer churn when only project source changes.
- **Image not retained as a registry artifact** — `zeeker-frontend:phase-02-test` was a verification-only tag. Plan 02-04 will define the production tag via `docker compose build`. Keeping the test image around would create stale-tag confusion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `COPY README.md ./README.md` to Dockerfile**
- **Found during:** Task 2 (first `docker build` attempt)
- **Issue:** Build failed at `RUN uv sync --frozen --no-cache` (the project-install step) with `OSError: Readme file does not exist: README.md`. Hatchling validates the `readme` field at wheel-build time and the README wasn't in WORKDIR yet — the original Dockerfile (matching RESEARCH Pattern 4 verbatim) only COPY'd `pyproject.toml`, `uv.lock`, and `src/`.
- **Fix:** Added `COPY README.md ./README.md` between the `COPY src/ ./src/` line and the second `uv sync`. Build succeeded on retry; the README is small and not security-sensitive, so adding it to the build context is a benign fix.
- **Files modified:** packages/zeeker-frontend/Dockerfile (added one COPY line + a comment explaining why)
- **Verification:** Re-ran `docker build`; layer 7/8 succeeded with `Built zeeker-frontend @ file:///app`; layer 8/8 installed the package; image manifest emitted; standalone `docker run` smoke test returned the expected JSON.
- **Committed in:** 7deab3f (Task 2 commit — fix landed in the same commit as the file's initial creation since the Dockerfile didn't exist before this task)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Trivial. The fix is additive (one COPY line + one comment), doesn't change the architectural fence, and brings the Dockerfile in line with what hatchling actually needs. RESEARCH Pattern 4 should be updated to include the README copy step for future plans that copy this pattern verbatim.

## Issues Encountered

- Docker build initial failure (covered above as the Rule 3 deviation). Root-caused on first error message; no debugging loop required.

## User Setup Required

None — no external service configuration required for this plan. The frontend container is currently a build artifact only; it will be wired into compose in Plan 02-04 with no inherited env vars (per CONTEXT.md and RESEARCH Pitfall 5: frontend `environment:` block stays empty).

## Next Phase Readiness

**Plan 02-04 is unblocked:**
- `packages/zeeker-frontend/Dockerfile` exists at the path Plan 02-04 needs for `build.context: ./packages/zeeker-frontend`.
- `uv.lock` is committed, so Plan 02-04's first compose-built image will use `uv sync --frozen` deterministically (no first-build lock-generation race).
- Service exposes port 8000 internally; healthcheck target `/frontend-test` returns the documented JSON within ~1s of cold start.
- Tests pass on the host (`cd packages/zeeker-frontend && uv run pytest -q` → 3 passed in 0.01s).

**Plan 02-05 verification will pass:**
- `verify_phase_02.sh`'s no-sqlite assertion (Plan 02-01 §11) will succeed: image was built from this Dockerfile and the binary is verifiably absent.
- `pyproject.toml` and `uv.lock` both grep-clean for `sqlite|datasette` (case-insensitive).

**No blockers.** Plan 02-03 (root Caddyfile) was sequenced after this plan; the frontend doesn't need to know about Caddy yet.

## Self-Check: PASSED

- [x] `packages/zeeker-frontend/pyproject.toml` exists — FOUND
- [x] `packages/zeeker-frontend/uv.lock` exists (192KB, non-empty) — FOUND
- [x] `packages/zeeker-frontend/Dockerfile` exists — FOUND
- [x] `packages/zeeker-frontend/src/zeeker_frontend/main.py` exists — FOUND
- [x] `packages/zeeker-frontend/src/zeeker_frontend/templates/.gitkeep` exists — FOUND
- [x] `packages/zeeker-frontend/src/zeeker_frontend/static/.gitkeep` exists — FOUND
- [x] `packages/zeeker-frontend/tests/test_frontend.py` exists — FOUND
- [x] Commit `b536f64` (Task 1) in git log — FOUND
- [x] Commit `7deab3f` (Task 2) in git log — FOUND
- [x] `cd packages/zeeker-frontend && uv run pytest -q` exits 0 with "3 passed" — VERIFIED
- [x] `docker build` exited 0; built image had no sqlite3 binary — VERIFIED (test image then removed)
- [x] No sqlite/datasette references in pyproject.toml or uv.lock — VERIFIED
- [x] No apt-get/libsqlite/install curl/install wget RUN instructions in Dockerfile — VERIFIED

---
*Phase: 02-dual-service-bring-up*
*Completed: 2026-04-20*

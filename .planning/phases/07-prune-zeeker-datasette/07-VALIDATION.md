---
phase: 7
slug: prune-zeeker-datasette
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-26
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (frontend) + bash integration verifiers (`scripts/verify_phase_*.sh`) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` (pytest), `scripts/` (verifiers) |
| **Quick run command** | `cd packages/zeeker-frontend && uv run pytest -q` |
| **Full suite command** | `cd packages/zeeker-frontend && uv run pytest -q && bash scripts/verify_phase_06.sh && bash scripts/verify_phase_07.sh` |
| **Estimated runtime** | ~10–20 seconds (pytest) + 30–60 seconds (verifiers + container restarts) |

Phase 7 deletes server-side surface; the byte-parity contract (`verify_api_parity.sh`) is the load-bearing test for the prune. Frontend pytest suite is unaffected by the prune (frontend doesn't import anything from the deleted files).

---

## Sampling Rate

- **After every task commit:** Run quick `pytest -q` against the frontend; verify the relevant section of `scripts/verify_phase_07.sh` if the task touched datasette image inputs.
- **After every plan wave:** Run full suite (`pytest` + Phase 6 verifier + Phase 7 verifier) against a freshly rebuilt datasette image (`docker compose up -d --build zeeker-datasette`).
- **Before `/gsd-verify-work`:** Full suite must be green; `verify_api_parity.sh` against `phase-07-pre/` baseline must exit 0.
- **Max feedback latency:** ~90 seconds end-to-end.

---

## Per-Task Verification Map

(Filled in by gsd-planner during plan generation. Each PLAN.md task gets a row here mapping `task_id → plan → wave → requirement → automated command`.)

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _(planner-fill)_ | | | | | | | | | |

---

## Specific Phase 7 contracts (must hold post-prune)

1. **Byte-parity (REQ-api-byte-parity):** Every fixture under `.planning/baselines/phase-07-pre/` returns identical bytes after the prune. Diffs in `/-/metadata.json` are the EXPECTED edit (fewer keys); fixture is captured AFTER metadata.json edit but BEFORE mass-delete.
2. **Frontend nav unbroken (REQ-frontend-route-set):** `/-/metadata.json` still returns `menu_links` array with the 5 frontend routes. Frontend `base.html` continues to render the dark nav.
3. **D-01 boundary (REQ-internal-only-datasette-exposure):** `/-/search` and `/-/sql` (Datasette-native dev surfaces) still return 200 via Caddy after the prune. Datasette's bundled defaults render without the M1 overlay.
4. **No re-overlay drift:** `scripts/download_from_s3.py` no longer redownloads `templates/`/`static/`/`plugins/` on container restart (load-bearing fix per researcher Q3 option a).
5. **Frontend pytest:** 165 tests still pass (no frontend code changes; this is a regression gate).

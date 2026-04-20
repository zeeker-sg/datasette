---
phase: 02-dual-service-bring-up
plan: 01
subsystem: infra
tags: [bash, docker, datasette, baselines, parity-check]

requires:
  - phase: 01-editorial-shell-home-inventory
    provides: V2 light theme deployment topology (single-service datasette) — captured baselines target this stack
provides:
  - Wave-0 verifier scripts (capture_baseline.sh, verify_api_parity.sh, verify_phase_02.sh)
  - 13 pre-mutation API baselines committed to .planning/baselines/phase-02/
  - Empirical ground truth for REQ-api-byte-parity verification in Plan 02-05
affects: [02-04 docker-compose mutation, 02-05 ship/no-ship verification, future phase-N parity work]

tech-stack:
  added: [bash + jq + curl scripts; .planning/baselines/ convention]
  patterns: [baseline-then-mutate verification pattern; .url sidecars for endpoint replay]

key-files:
  created:
    - scripts/capture_baseline.sh
    - scripts/verify_api_parity.sh
    - scripts/verify_phase_02.sh
    - .planning/baselines/phase-02/README.md
    - .planning/baselines/phase-02/.gitkeep
    - 13 baseline JSON files + 13 .url sidecars under .planning/baselines/phase-02/
  modified: []

key-decisions:
  - "Capture baselines BEFORE any compose mutation (sequencing gate, not just policy)"
  - "Use .url sidecar files so verify_api_parity.sh can replay each endpoint without re-deriving paths"
  - "Strip volatile fields (query_ms, __time__, request_duration_ms) via jq before diff; treat /-/versions.json as structural-only diff"
  - "Reference actual compose service name `zeeker-datasette` in verify_phase_02.sh (not PRD/research placeholder `datasette`)"

patterns-established:
  - "Baseline-then-mutate: every compose/topology change in this milestone (M2) starts by capturing pre-state baselines, then asserts post-state matches modulo volatile fields"
  - "Verifier scripts fail-fast and surface root cause (e.g., 'cannot reach http://localhost — Caddy not up?') instead of returning empty diffs"
  - "Hidden-dotfile baseline naming (`.json.json` for the `/.json` database index) — quirky but lossless; tooling that needs full enumeration must use `ls -a` or explicit globs"

requirements-completed:
  - REQ-api-byte-parity
  - REQ-incremental-migration
  - REQ-internal-only-datasette-exposure
  - REQ-frontend-data-via-http

duration: ~4min
completed: 2026-04-21
---

# Plan 02-01: Wave-0 Validation Infrastructure Summary

**13 pre-mutation API baselines committed + three verifier scripts (capture, parity, phase-02) ready for use by Plans 02-04 and 02-05**

## Performance

- **Duration:** ~4 minutes (executor wall time)
- **Started:** 2026-04-20 (during /gsd-execute-phase 2 invocation)
- **Completed:** 2026-04-21 (after human checkpoint approval)
- **Tasks:** 3 (2 autonomous + 1 human-verified checkpoint)
- **Files modified:** 4 scripts + 13 baseline JSON + 13 URL sidecars + 2 metadata files = 32 files

## Accomplishments

- Three verifier scripts authored and committed: `scripts/capture_baseline.sh` (pre-mutation snapshot), `scripts/verify_api_parity.sh` (post-Caddy diff), `scripts/verify_phase_02.sh` (full Phase-2 acceptance harness — 11 assertions wrapped).
- 13 baseline JSON files captured against the live single-service Datasette at `localhost:8001` (datasette `0.65.1`), covering all 3 databases (`sg-gov-newsrooms`, `sglawwatch`, `zeeker-judgements`) plus 4 metadata endpoints (`/-/versions`, `/-/metadata`, `/-/plugins`, `/.json`) and 6 table endpoints (size=10).
- 13 matching `.url` sidecars committed so `verify_api_parity.sh` can replay each endpoint deterministically without re-deriving paths.
- Service-name correction enforced: every script references `zeeker-datasette` (the actual compose service name) rather than the research/PRD placeholder `datasette`. Verified by inspection of all three scripts.
- Graceful failure modes confirmed: `verify_api_parity.sh` exits 1 with a clear "Caddy not up?" message when localhost:80 is unreachable — proving the post-mutation verifier won't silently pass on a half-deployed stack.

## Task Commits

1. **Task 1: Create scripts/capture_baseline.sh + commit pre-mutation baselines** — `efdd3d5` (feat)
2. **Task 2: Create scripts/verify_api_parity.sh + scripts/verify_phase_02.sh + URL sidecars** — `4036226` (feat)
3. **Task 3: Human checkpoint** — approved 2026-04-21 by user. No commit; checkpoint approval recorded in this SUMMARY.

## Files Created/Modified

- `scripts/capture_baseline.sh` — captures JSON for the canonical URL set against `http://localhost:8001`; applies jq strip filter for volatile fields; emits `.url` sidecars
- `scripts/verify_api_parity.sh` — diffs current responses (against `http://localhost`, post-Caddy) against committed baselines; treats `/-/versions.json` as structural-only diff
- `scripts/verify_phase_02.sh` — wraps 11 phase-2 acceptance assertions; invokes `verify_api_parity.sh` as the final gate
- `.planning/baselines/phase-02/.gitkeep` — directory marker
- `.planning/baselines/phase-02/README.md` — explains baseline lifecycle and replay convention
- `.planning/baselines/phase-02/*.json` × 13 — pre-mutation API responses (one hidden dotfile `.json.json` for `/.json` index)
- `.planning/baselines/phase-02/*.url` × 13 — endpoint URL sidecars

## Decisions Made

- **Sequencing as a gate, not a guideline:** Baselines were captured against the CURRENT single-service stack BEFORE any other Phase-2 work touched compose. If we'd captured after Plan 02-04's mutation, the baselines would be the post-state and parity verification would be circular.
- **`.url` sidecar pattern over hardcoded URL list in verify script:** The list of endpoints lives next to the baseline data, not in script logic. Adding/removing endpoints in future runs is a `capture_baseline.sh` edit + commit, not a coordinated edit across two scripts.
- **`zeeker-datasette` service name everywhere:** Caught at plan-time (planner verified vs research's placeholder) and reinforced at execution-time (verify_phase_02.sh greps for the actual name). Eliminates the most likely "looks done but isn't" trap from research's Risk register.

## Deviations from Plan

None — plan executed exactly as written. The minor `capture_baseline.sh` edit during Task 2 to emit `.url` sidecars was anticipated by the plan and committed as part of Task 2.

## Issues Encountered

- Initial `/gsd-execute-phase 2` invocation found Docker daemon and datasette stack down. Resolved by `open -a Docker` + waiting for daemon + `docker compose up -d`; datasette became healthy in ~10 seconds. Not a plan defect — environment was simply not pre-warmed.

## User Setup Required

None — no external service configuration required for this plan. (Phase 2 overall will need the `.env` file with S3 + AWS + Matomo vars, but that already exists per the existing single-service deployment.)

## Next Phase Readiness

**Wave 2 ready to spawn:**
- Plan 02-02 (`packages/zeeker-frontend/` scaffold) and Plan 02-03 (root `Caddyfile`) can run in parallel — no `files_modified` overlap, no inter-plan dependencies.
- Plan 02-04 (compose mutation) is gated on both Wave 2 plans completing; `git revert` of 02-04's single commit is the documented rollback path.
- Plan 02-05 (final ship/no-ship checkpoint) depends on all earlier waves; the verifier scripts and baselines from this plan are its primary inputs.

**No blockers.** Docker daemon is up; datasette is healthy; baselines are committed; scripts are syntax-valid and have been smoke-tested for graceful failure.

---
*Phase: 02-dual-service-bring-up*
*Completed: 2026-04-21*

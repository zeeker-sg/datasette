---
phase: 03-flip-suffix-based-routing
plan: 04
subsystem: infra
tags: [caddy, routing, parity-verification, ship-gate, stale-check-cleanup]

requires:
  - phase: 02-dual-service-bring-up
    provides: Three-service Docker topology + verifier script pattern + post-Caddy parity baselines
provides:
  - Activated Phase-3 suffix routing (`*.json|*.csv|*.db|/-/* → datasette`, else → frontend)
  - Empirical proof of REQ-suffix-routing-contract (11 negative + 7 positive routing assertions, body-content fallthrough sniff, 12/12 parity diff clean)
  - Stale-check cleanup: verify_phase_02.sh check #3 jq filter fix + check #10 polarity inversion
affects: [04-port-home-database (next phase, deploys + first HTML routes), 05-port-table-row, 06-port-aux-pages, 07-prune-zeeker-datasette]

tech-stack:
  added: []
  patterns:
    - "Stale-check retirement in same phase that obsoletes them (don't let inheritance fail forward)"
    - "Body-content fallthrough sniff over status-code-only verification"

key-files:
  created:
    - .planning/phases/03-flip-suffix-based-routing/03-04-bringup-log.txt
    - .planning/phases/03-flip-suffix-based-routing/03-04-parity-log.txt
    - .planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md
    - .planning/phases/03-flip-suffix-based-routing/03-04-SUMMARY.md
  modified:
    - scripts/verify_phase_02.sh (check #3 jq filter fixed; check #10 inverted post-Phase-3)

key-decisions:
  - "Categorical triage: Phase-2 verifier failures (#3 + #10) classified as INHERITANCE issues, not Phase-3 regressions; fix-in-this-phase chosen over defer-to-followup for cleanliness"
  - "verify_phase_02.sh check #3 jq filter widened to exclude EXPOSE-only entries (PublishedPort: 0); previously falsely flagged any service with EXPOSE in its Dockerfile"
  - "verify_phase_02.sh check #10 polarity inverted from 'expects 404 from datasette' to 'expects 200 from frontend with placeholder JSON' — this is what Phase 3 ships"
  - "Ship recommendation: zero Category-D regressions; all load-bearing tests green"

patterns-established:
  - "Phase-N verifier delegates to Phase-(N-1) verifier as topology-invariant inheritance check"
  - "Stale Phase-(N-1) sentinels that flip polarity by Phase-N's design get retired in the SAME phase that obsoletes them, not deferred"

requirements-completed:
  - REQ-suffix-routing-contract
  - REQ-api-byte-parity
  - REQ-incremental-migration

duration: ~10min (executor + post-checkpoint stale-check fixes + re-run)
completed: 2026-04-21
---

# Plan 03-04: Restart + Verify + Ship Summary

**Phase 3 SHIPPED 2026-04-21 — suffix routing live (`*.json|*.csv|*.db|/-/*` → datasette, else → frontend); 11/11 negative + 7/7 positive routing checks pass with body-content fallthrough sniff; 12/12 baselines byte-identical; verify_phase_02.sh stale checks #3 + #10 retired**

## Performance

- **Duration:** ~10 minutes total (executor pass: ~6 min including checkpoint; orchestrator post-ship: ~4 min for stale-check fixes + re-verify + commit)
- **Started:** 2026-04-21 (after `/gsd-execute-phase 3`)
- **Completed:** 2026-04-21 (after operator ship + stale-check fixes)
- **Tasks:** 3 (2 autonomous + 1 human-verified checkpoint)
- **Files modified:** 4 new + 1 modified = 5 files

## Accomplishments

- **Phase-3 routing activated** — `docker compose restart caddy` loaded the new Caddyfile (`@datasette` matcher + catch-all to frontend); all 3 services healthy in 14s; in-container Caddyfile confirmed `@datasette` block present.
- **`verify_phase_03.sh` exit 0** — 7 positive routing checks (`*.json`, `*.csv`, `*.db`, `/-/*` reach datasette), 11 negative routing checks (HTML routes return frontend 404; ALL pass body-content fallthrough sniff for `zeeker-base.css`), 4 edge cases (multi-dot+query, HEAD/GET, case-insensitive `.JSON`, CORS preserved), Phase-2 verifier delegation, parity wrap.
- **`verify_api_parity.sh` exit 0** — 12/12 baselines diff cleanly. Zero drift. Materially better than Phase 2's gate (which had Cat A/B/C drifts).
- **REQ-suffix-routing-contract verified at the load-bearing layer** — body-content fallthrough sniff (the test designed to catch silent fallthrough that status codes alone miss) passed all 11 negative-routing assertions.
- **Stale-check cleanup landed** — `verify_phase_02.sh` checks #3 + #10 retired in this phase (not deferred), so future Phase-N runs inherit a green Phase-2 verifier.
- **Live smoke checks all green** (operator-verifiable):
  - `curl http://localhost/` → 404 with `{"detail":"Not Found"}` (frontend)
  - `curl http://localhost/sglawwatch` → 404 with `{"detail":"Not Found"}` (frontend, no `zeeker-base.css` fingerprint)
  - `curl http://localhost/sglawwatch.json` → 200 (datasette)
  - `curl http://localhost/-/versions.json | jq .datasette.version` → `0.65.2` (datasette)
  - `curl http://localhost/frontend-test` → 200 + `{"status":"ok","service":"zeeker-frontend"}` (frontend)

## Task Commits

The atomic ship commit follows this SUMMARY (logs + summary + test plan + verifier-script fixes in one commit). Per Plan 04's protocol, commits did NOT happen during execution — they happen post-checkpoint approval.

## Files Created/Modified

- `.planning/phases/03-flip-suffix-based-routing/03-04-bringup-log.txt` — full forensic log of restart + initial verifier run (exit 1 due to inherited Phase-2 issues) + post-fix re-run (exit 0)
- `.planning/phases/03-flip-suffix-based-routing/03-04-parity-log.txt` — standalone verify_api_parity.sh log (exit 0, 12/12 PASS)
- `.planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md` — repeatable Phase-3 verification recipe (5 sections: preconditions → Caddyfile edit → restart → verify → rollback)
- `.planning/phases/03-flip-suffix-based-routing/03-04-SUMMARY.md` (this file)
- `scripts/verify_phase_02.sh` — check #3 jq filter widened; check #10 polarity inverted (200 + frontend JSON expected post-Phase-3)

## Decisions Made

### Triage methodology applied (Phase-2 Categories A/B/C/D)

Initial `verify_phase_03.sh` exit 1. Two failures triaged:

| Failure | Category | Reason | Verdict |
|---------|----------|--------|---------|
| `verify_phase_02.sh` check #3 — flagged frontend + datasette as "publishing ports" | **B-adjacent (tooling drift)** — known Phase-2 verifier bug, documented in `02-05-SUMMARY.md` | jq filter `length > 0` matched EXPOSE-only `Publishers` entries with `PublishedPort: 0` | Ship-able; fix in this phase per operator request |
| `verify_phase_02.sh` check #10 — `/frontend-test` returned 200, expected 404 | **NOT a regression — INTENDED behavior change.** | Pre-flip: Caddy transparent-proxied to datasette (404 from datasette). Post-flip: Caddy routes to frontend (200 with placeholder JSON). The check was a Phase-2 forward-compat sentinel that had reached its sunset by Phase-3 design | Ship-able; invert in this phase per operator request |

**Category D (real topology-induced API regression) count: ZERO.**

### Stale-check fixes detail

**Check #3 (line 36-44 of verify_phase_02.sh):**
- Before: `select((.Publishers | length) > 0)` matched any service with at least one Publishers entry, including EXPOSE-only entries with `PublishedPort: 0`.
- After: `select(([.Publishers[] | select(.PublishedPort > 0)] | length) > 0)` filters to entries with a real published port before counting.

**Check #10 (line 105-119 of verify_phase_02.sh):**
- Before: asserted HTTP 404 for `http://localhost/frontend-test` (correct when Caddy transparent-proxied everything; broken when Caddy routes by suffix).
- After: asserts HTTP 200 + body contains `"service":"zeeker-frontend"` (correct post-Phase-3; would fail if Phase-3 routing flip is rolled back, which is the right semantic — the check is now a positive Phase-3 invariant assertion).
- Comment block above the check documents the inversion rationale and date.

### Operator-requested option chosen

User selected "Ship + retire stale checks" from the checkpoint options. Cleanup landed in this phase rather than a deferred housekeeping plan — keeps the inheritance chain honest: Phase 4+ executor agents won't waste effort triaging Phase-2 verifier failures that should have been retired.

## Deviations from Plan

**1 auto-applied (operator-directed):** Stale-check fixes to `verify_phase_02.sh` (`scripts/verify_phase_02.sh` modified) were NOT in Plan 04's `files_modified` list. The plan envisioned only forensic-log + SUMMARY + TEST-PLAN edits. Operator's selection of "Ship + retire stale checks" at the checkpoint authorized the additional file modification. Documented here per deviation-rule conventions.

## Issues Encountered

- Initial `verify_phase_03.sh` run exited 1 due to two Phase-2 inheritance issues (described in Decisions Made above). Triaged as non-regressions. Fixed in same commit as ship.

## User Setup Required

None — no external service configuration changed.

## Next Phase Readiness

**Phase 4 (Port home + database pages) ready to start:**
- Suffix routing is live; HTML requests now hit frontend (which only serves `/frontend-test` and 404s on everything else). Phase 4's job is to fill in `/` and `/{db}` so users see the V2 editorial design served from FastAPI/Jinja.
- M1's V2 templates (`templates/index.html` from sketch 001-D, `templates/database.html` from sketch 002-B) are reference material to harvest into Jinja templates under `packages/zeeker-frontend/src/zeeker_frontend/templates/`.
- M1 CSS (`static/css/zeeker-base.css`) needs to migrate to `packages/zeeker-frontend/src/zeeker_frontend/static/zeeker.css` — the datasette package keeps the original until Phase 7 (prune).
- Production deploy ships in Phase 4 (the first phase with user-visible HTML changes).
- Re-baseline against post-Phase-3 stack for Phase 4's parity reference is recommended (parity is currently clean against `phase-03-pre/`, but Phase 4 will introduce frontend HTML routes that have no parity equivalent and the API routes won't change shape — re-baselining is more about ergonomics than necessity).

**No blockers.** Stack live, verifier suite all green, working tree about to be clean post-commit.

---
*Phase: 03-flip-suffix-based-routing*
*Completed: 2026-04-21*

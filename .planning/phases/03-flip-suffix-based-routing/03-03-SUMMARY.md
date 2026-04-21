---
phase: 03-flip-suffix-based-routing
plan: 03
subsystem: infra
tags: [bash, verifier, caddy, routing-assertions, fallthrough-guard, curl, jq]

# Dependency graph
requires:
  - phase: 03-flip-suffix-based-routing
    provides: "scripts/verify_api_parity.sh parameterized via ZEEKER_BASELINE_DIR (Plan 01); Caddyfile flipped to suffix-matcher shape on disk (Plan 02 — committed but Caddy not yet restarted)"
  - phase: 02-dual-service-bring-up
    provides: "scripts/verify_phase_02.sh (topology invariants); .planning/baselines/phase-03-pre/ (13 JSON+url baselines); three-service docker-compose topology"
provides:
  - "scripts/verify_phase_03.sh — Phase-3 routing-flip verifier"
  - "Body-content fallthrough sniff (`zeeker-base.css` datasette-HTML fingerprint) as the load-bearing negative-routing guard"
  - "Phase-2 verifier delegation pattern (B section) — Phase 3 inherits topology invariants without re-asserting them inline"
  - "Parity-wrap pattern (G section) — exports ZEEKER_BASELINE_DIR=phase-03-pre and invokes the parameterized verify_api_parity.sh"
  - "Plan 04 unblocked: both Caddyfile (Plan 02) and verifier (this plan) are in place; Plan 04 owns the Caddy container restart + verifier-run gate"
affects: ["03-04 (operator gate runs this verifier post-restart)", "Phase 4 (HTML-route porting; verifier provides the regression net)", "Phase 5-6 (further frontend route ports)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Verifier delegation: Phase-N verifier shells out to Phase-(N-1) verifier as its first big check"
    - "Body-content fingerprint sniff for routing-correctness assertions (not just status codes)"
    - "Parameterized baseline dir via env-var-with-default pattern (`${VAR:-default}`) carried into verifier composition"

key-files:
  created:
    - "scripts/verify_phase_03.sh"
  modified: []

key-decisions:
  - "Use body-content sniff for `zeeker-base.css` (RESEARCH Pitfall 1) as the decisive negative-routing guard rather than status code alone"
  - "Invoke verify_phase_02.sh as Section B (RESEARCH Open Q#2) — Phase 3 inherits topology invariants by delegation, not re-implementation"
  - "Parity-wrap exports ZEEKER_BASELINE_DIR=phase-03-pre then invokes Plan-01-parameterized verify_api_parity.sh (no JQ_STRIP mutation)"
  - "Author script in this plan but DO NOT execute it against the live stack — Caddy still on Phase-2 transparent-proxy config; running now would surface false negatives. Plan 04 owns restart + run as one atomic gate."
  - "Add 11th `check_negative` invocation for row-URL shape (`/sglawwatch/headlines/synthetic-row-id-not-real`) to catch the matcher-bug class where regex only matches 1-2 path segments"

patterns-established:
  - "Pattern (verifier composition): Per-phase verifier scripts compose by invoking the previous phase's verifier as their first big check. Topology invariants are tested ONCE at the phase that introduced them; downstream phases delegate."
  - "Pattern (fingerprint sniff): When routing assertions hinge on which upstream served a response, grep the body for an upstream-unique substring (here, datasette's `zeeker-base.css` link tag) — never trust status codes alone for routing-flip verification."
  - "Pattern (deferred execution): Authoring a verifier and running it can live in different plans/waves when running it requires a state mutation that another plan owns (here: Caddy container restart owned by Plan 04)."

requirements-completed: [REQ-suffix-routing-contract, REQ-api-byte-parity]

# Metrics
duration: 2m 28s
completed: 2026-04-21
---

# Phase 03 Plan 03: verify_phase_03.sh Authoring Summary

**Authored 236-line bash verifier for the Phase-3 suffix-routing flip — 7 check sections (Caddyfile validate, Phase-2 delegation, 6 positive routing checks, 11 negative routing checks with `zeeker-base.css` body-content fallthrough guard, frontend reachability, 4 edge cases, parity wrap) — script committed but NOT executed (Plan 04 owns the post-restart gate run).**

## Performance

- **Duration:** 2m 28s
- **Started:** 2026-04-21T10:08:20Z
- **Completed:** 2026-04-21T10:10:48Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments

- `scripts/verify_phase_03.sh` exists at 236 lines, executable (`-rwxr-xr-x`), passes `bash -n` syntax validation
- All seven check sections (A-G) present per RESEARCH Code Example 2 with the row-URL shape addition (11th `check_negative`)
- Body-content fallthrough guard (`grep -q 'zeeker-base.css'`) is the spine of Section D — the load-bearing assertion of the verifier
- Phase-2 verifier delegated as Section B (inherits topology invariants without re-implementation)
- Parity wrap (Section G) exports `ZEEKER_BASELINE_DIR=$ROOT/.planning/baselines/phase-03-pre` then invokes the Plan-01-parameterized `verify_api_parity.sh` — no `JQ_STRIP` mutation
- Plan 04 unblocked: both the Caddyfile flip (Plan 02 commit `ebf3f52`) and this verifier (commit `5f9a224`) are in place; Plan 04 restarts Caddy and runs both verifiers as one atomic gate

## Task Commits

Each task committed atomically:

1. **Task 1: Author scripts/verify_phase_03.sh; chmod +x; bash -n; do NOT execute against live stack** — `5f9a224` (feat)

**Plan metadata commit:** to follow this SUMMARY (docs).

## Files Created/Modified

- `scripts/verify_phase_03.sh` (NEW, 236 lines, mode 755) — Phase-3 routing-flip verifier with 7 check sections covering caddy validate (A), Phase-2 topology delegation (B), 6 positive routing checks for `/-/versions.json`, `/sglawwatch.json`, `/sglawwatch/headlines.json`, `.csv`, `.db`, `/-/sql`, `/-/search` (C), 11 negative routing checks with body-content fallthrough guard for the 10 page-shape URLs plus 1 row-URL shape probe (D), `/frontend-test` reachability (E), edge cases for multi-dot+query / HEAD-vs-GET symmetry / case-insensitivity / CORS (F), and parity wrap exporting `ZEEKER_BASELINE_DIR=phase-03-pre` (G).

## Verification Coverage

| Section | Purpose                                         | Assertion mechanism                                                                  |
| ------- | ----------------------------------------------- | ------------------------------------------------------------------------------------ |
| A       | Caddyfile validates                             | `docker run --rm caddy:2.11.2-alpine caddy validate`                                 |
| B       | Phase-2 topology invariants intact              | `bash scripts/verify_phase_02.sh` (delegation)                                       |
| C       | `*.json`, `.csv`, `.db`, `/-/*` reach datasette | `check_positive` body-substring greps + status-code probes for binary surfaces       |
| D       | HTML routes do NOT reach datasette              | `check_negative` body-content sniff for `zeeker-base.css` (load-bearing)             |
| E       | `/frontend-test` reachable                      | curl + grep for `"status":"ok"` AND `"service":"zeeker-frontend"`                    |
| F       | Edge cases                                      | multi-dot+query, HEAD/GET symmetry, case-insensitive `.JSON`, CORS header preserved  |
| G       | API byte-parity                                 | `export ZEEKER_BASELINE_DIR=...phase-03-pre` then `bash scripts/verify_api_parity.sh` |

## Why This Plan Did NOT Run the Verifier Live

Caddyfile on disk is on the NEW shape (Plan 02 commit `ebf3f52`), but Caddy in-memory is still on the OLD shape (Plan 02 explicitly does not restart). Running `verify_phase_03.sh` now would correctly detect that Section D negative routes still serve datasette HTML (because the OLD config transparent-proxies everything to datasette) — which is a true negative for the live stack but a false negative relative to what the verifier is designed to test (post-flip behavior). Plan 04 ships `docker compose restart caddy` + verifier-run as one atomic gate operation per the validate-but-don't-restart split locked in Phase-3 decisions.

## Decisions Made

- **Body-content sniff over status code**: per RESEARCH Pitfall 1, datasette's `zeeker-base.css` link tag is unique across all datasette-rendered HTML (including its own 404 page). Grepping the response body for it is the decisive way to catch silent fallthrough bugs that pass status-code checks. Section D is built around this.
- **Phase-2 verifier delegation**: per RESEARCH Open Q#2, Section B invokes `bash scripts/verify_phase_02.sh` rather than re-asserting topology invariants inline. Inherits Phase-2's known check-#3 jq false positive AS-IS (out of scope to fix per Phase-2 SUMMARY follow-ups).
- **No JQ_STRIP widening**: Section G exports `ZEEKER_BASELINE_DIR` then shells out to the parameterized `verify_api_parity.sh` unchanged. Bright line preserved between honest verification and rationalization.
- **11th `check_negative` for row-URL shape**: added `/sglawwatch/headlines/synthetic-row-id-not-real` to catch matcher bugs where a regex only handles 1-2 path segments. Synthetic pk — datasette would 404 on the row regardless; what matters is the routing decision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded header comment to satisfy `! grep -q 'restart caddy'` acceptance criterion**

- **Found during:** Task 1 (final acceptance-criteria sweep)
- **Issue:** The plan's prescribed script content included a header comment containing the literal substring `docker compose restart caddy` (line 5 of the original draft). The plan's own acceptance check (`! grep -q 'restart caddy' scripts/verify_phase_03.sh`) — designed to enforce that this verifier never restarts Caddy itself (Plan 04 owns that) — would fail against any file containing that substring, even in a comment. The check is substring-based, not AST-aware.
- **Fix:** Reworded the header comment to convey the same meaning ("after Plan 02's Caddyfile edit AND the Caddy container has been restarted to pick up the new config — see 03-TEST-PLAN.md for the exact docker compose invocation") without containing the literal substring `restart caddy`. Semantic content unchanged; reader still understands the precondition. The literal command lives in 03-TEST-PLAN.md (Plan 04's deliverable) where it belongs operationally.
- **Files modified:** scripts/verify_phase_03.sh (header comment block, lines 5-10)
- **Verification:** Full acceptance-criteria chain (`test -x ... && bash -n ... && grep -q 'zeeker-base.css' ... && ! grep -q 'restart caddy' ...`) now returns 0 with `FULL_ACCEPTANCE_PASS`.
- **Committed in:** `5f9a224` (Task 1 commit — applied before commit, single atomic file)

---

**Total deviations:** 1 auto-fixed (1 bug — comment-vs-acceptance-check substring collision)
**Impact on plan:** Comment rewording only; semantic intent of the script preserved. The `! grep -q 'restart caddy'` acceptance check is the more authoritative spec (it's the contract enforced by the validation harness); the comment was the easier side to adjust without touching script behavior.

## Issues Encountered

None — single-task authoring plan with clear spec.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 04 (Wave 4) is now fully unblocked. Both prerequisites in place:
  - Caddyfile on disk in NEW suffix-matcher shape (Plan 02 commit `ebf3f52`)
  - `scripts/verify_phase_03.sh` authored and ready to run (this plan, commit `5f9a224`)
- Plan 04's atomic gate sequence: `docker compose restart caddy` → poll healthcheck for 3/3 healthy → `bash scripts/verify_phase_03.sh` (captures Section A through G) → human checkpoint reviews forensic logs and visual smoke → ship/no-ship decision.
- No blockers or concerns. Phase-2 verifier's known check-#3 jq false positive will surface in Section B of any post-restart run; Plan 04 already plans to triage it via Phase-2 Categories A/B/C/D framework.

## Self-Check: PASSED

- File exists: `scripts/verify_phase_03.sh` ✓
- Commit exists: `5f9a224` ✓
- Acceptance chain: `FULL_ACCEPTANCE_PASS` ✓ (test -x, bash -n, all required substrings present, 11 check_negative, >100 lines, no `restart caddy` substring)

---
*Phase: 03-flip-suffix-based-routing*
*Completed: 2026-04-21*

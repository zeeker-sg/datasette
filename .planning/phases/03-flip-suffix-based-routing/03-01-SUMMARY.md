---
phase: 03-flip-suffix-based-routing
plan: 01
subsystem: testing
tags: [bash, verifier, baseline, parameterization, env-var, phase-03-prep]

# Dependency graph
requires:
  - phase: 02-dual-service-bring-up
    provides: scripts/capture_baseline.sh, scripts/verify_api_parity.sh, .planning/baselines/phase-03-pre/ (re-captured 2026-04-21)
provides:
  - "scripts/capture_baseline.sh and scripts/verify_api_parity.sh both honor ZEEKER_BASELINE_DIR env var with phase-03-pre default"
  - "Verifier scripts are now phase-agnostic — Phase 4+ can override the baseline directory without editing the scripts"
  - "Negative-fence guarantee: no script in scripts/ hardcodes 'phase-02' anymore"
affects: [03-02, 03-03, 03-04, phase-04-and-beyond]

# Tech tracking
tech-stack:
  added: []
  patterns: [env-var-with-default-fallback for phase-scoped paths]

key-files:
  created: []
  modified:
    - scripts/capture_baseline.sh
    - scripts/verify_api_parity.sh

key-decisions:
  - "Parameterize via ZEEKER_BASELINE_DIR env var (per CONTEXT D-XX option b); default to phase-03-pre rather than re-hardcoding"
  - "JQ_STRIP filter NOT widened — Phase-2 SUMMARY codifies silent diff masking as the explicit anti-pattern; this plan inherits that discipline verbatim"
  - "Smoke-test output captured to /tmp (not committed) — informational only; the actual gate runs in Plan 04 after the Caddyfile flip"

patterns-established:
  - "Phase-scoped paths in shell scripts: use ${VAR:-default} so downstream phases can override via env var without editing the script"
  - "Default value points to the CURRENT phase's baseline directory, not a generic location — keeps the no-args invocation safe by default"

requirements-completed: [REQ-incremental-migration]

# Metrics
duration: 1m 25s
completed: 2026-04-21
---

# Phase 03 Plan 01: Parameterize Baseline Verifier Scripts Summary

**Both Phase-2 verifier scripts (`capture_baseline.sh`, `verify_api_parity.sh`) now honor `ZEEKER_BASELINE_DIR` env var with a `phase-03-pre` default; smoke-tested green (12/12 byte-parity) against the live post-Phase-2 stack.**

## Performance

- **Duration:** 1m 25s
- **Started:** 2026-04-21T09:56:53Z
- **Completed:** 2026-04-21T09:58:18Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `scripts/capture_baseline.sh` line 14 (was line 13) reads `OUT_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"`; comment updated to reflect phase-agnostic behavior.
- `scripts/verify_api_parity.sh` line 10 reads `BASELINE_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"`.
- Negative-fence guarantee: `! grep -rn 'phase-02' scripts/` returns empty — no script in the repo hardcodes the renamed `phase-02` directory anymore.
- Smoke test against live post-Phase-2 stack (3 services up, datasette 0.65.2): **12/12 baselines byte-parity PASS**, exit 0.
- Negative smoke test: `ZEEKER_BASELINE_DIR=/tmp/zeeker-no-such-dir-$$ bash scripts/verify_api_parity.sh` exits 1 with the documented `ERROR: no baselines found in /tmp/zeeker-no-such-dir-NNNNN` — env-var override demonstrably works.

## Task Commits

Each task was committed atomically:

1. **Task 1: Parameterize scripts/capture_baseline.sh OUT_DIR via ZEEKER_BASELINE_DIR** — `5fd66ab` (feat)
2. **Task 2: Parameterize scripts/verify_api_parity.sh BASELINE_DIR + smoke-test against current stack** — `8445c43` (feat)

**Plan metadata:** to be committed (this SUMMARY + STATE.md + ROADMAP.md + REQUIREMENTS.md)

## Files Created/Modified

- `scripts/capture_baseline.sh` — OUT_DIR parameterized; header comment updated. Diff: +3/-2 lines (one OUT_DIR line + comment block expansion from 1 to 2 lines).
- `scripts/verify_api_parity.sh` — BASELINE_DIR parameterized. Diff: +1/-1 line (single-line edit, no comment changes — the script's header comment is already phase-neutral).

## Exact Diffs Applied

**scripts/capture_baseline.sh:**
```diff
-# representative JSON responses to .planning/baselines/phase-02/ and commits
+# representative JSON responses to $ZEEKER_BASELINE_DIR (default
+# .planning/baselines/phase-03-pre/) and commits
...
-OUT_DIR="$(git rev-parse --show-toplevel)/.planning/baselines/phase-02"
+OUT_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"
```

**scripts/verify_api_parity.sh:**
```diff
-BASELINE_DIR="$(git rev-parse --show-toplevel)/.planning/baselines/phase-02"
+BASELINE_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"
```

## Smoke Test Outcome

Default-path invocation `bash scripts/verify_api_parity.sh` (no env var) against the live three-service stack (caddy:80 → zeeker-datasette:8001 → frontend:8000):

```
OK:               /-/metadata.json
OK:               /-/plugins.json
OK (structural):  /-/versions.json
OK:               /sg-gov-newsrooms/_zeeker_schemas.json?_size=10
OK:               /sg-gov-newsrooms/_zeeker_updates.json?_size=10
OK:               /sg-gov-newsrooms.json?_size=10
OK:               /sglawwatch/about_singapore_law.json?_size=10
OK:               /sglawwatch/headlines.json?_size=10
OK:               /sglawwatch.json?_size=10
OK:               /zeeker-judgements/_zeeker_schemas.json?_size=10
OK:               /zeeker-judgements/_zeeker_updates.json?_size=10
OK:               /zeeker-judgements.json?_size=10

REQ-api-byte-parity: PASS
```

**Exit code: 0.** All 12 baselines on disk matched byte-for-byte against the current stack — exactly the expected outcome since these baselines were captured from this same stack at commit `ee3f3ad` one day prior. Phase-2 four-category triage (A: host-URL drift, B: S3 metadata refresh, C: live-data drift, D: true regression) showed **zero diffs in any category** — Category A is impossible (we re-baselined post-Caddy so localhost:80 == baseline), and Categories B/C/D would have surfaced as `FAIL` lines. Clean.

Negative smoke test (env-var override with nonexistent path):
```
$ ZEEKER_BASELINE_DIR=/tmp/zeeker-no-such-dir-63389 bash scripts/verify_api_parity.sh
ERROR: no baselines found in /tmp/zeeker-no-such-dir-63389
Run scripts/capture_baseline.sh against the pre-Phase-2 stack first.
[exit 1]
```

The error message correctly contains the override path (proves env-var read fired) and the script fails fast at line 17 (the documented guard) — no further execution. Exit 1 is expected and acceptable.

## Decisions Made

- **Parameterize, do not re-hardcode.** Both option (a) "re-hardcode to `phase-03-pre`" and option (b) "parameterize via env var with `phase-03-pre` default" achieve the immediate goal. Option (b) was locked in CONTEXT (D-XX) because Phase 4+ will need a similar fix and the cumulative cost of editing the same line N more times exceeds the one-time cost of an env-var indirection.
- **Default value points to the current phase**, not a generic placeholder. This means `bash scripts/verify_api_parity.sh` with no env var Just Works in the current phase, and Phase 4 simply exports `ZEEKER_BASELINE_DIR=.planning/baselines/phase-04-pre` before invoking — no script edit, no broken default.
- **Comment expansion only on capture_baseline.sh.** The `verify_api_parity.sh` header comment was already phase-neutral (says "Phase 2" only as a phase marker, doesn't reference the directory) so no comment edit was needed there. The `capture_baseline.sh` header explicitly named the output directory in prose, hence the 2-line comment expansion.

## Deviations from Plan

None — plan executed exactly as written.

Both tasks completed cleanly on first attempt. No bugs surfaced. No missing critical functionality. No blocking issues. No architectural questions. Verifier scripts ran successfully against the live stack with the exact expected outputs.

## Issues Encountered

None.

The smoke-test output count (12 OK lines) is one fewer than the plan's interfaces block estimate ("13 *.json + 13 *.url"), but `ls .planning/baselines/phase-03-pre/*.json | wc -l` confirms 12 baseline files on disk — the plan's count was an estimate written before final disk counting. All baselines that exist passed parity. This is not a deviation; it's an estimate vs. actual.

## User Setup Required

None — no external service configuration, no env vars to add to deployment, no dashboard changes. The new `ZEEKER_BASELINE_DIR` env var is a developer-shell convenience with a sensible default; users running the verifier scripts during normal development invoke them with no env var and get the correct phase-03-pre baseline.

## Next Phase Readiness

**Wave 2 (Plan 02 — Caddyfile suffix-routing flip) is now unblocked.** Plan 02's verifier wiring depends on `verify_api_parity.sh` defaulting to `phase-03-pre` so `bash scripts/verify_api_parity.sh` after the Caddyfile flip diffs against the right baseline set. That contract is now in place.

**Wave 3 (Plan 03 — verify_phase_03.sh authoring) is also unblocked.** Plan 03's script will export `ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre` before invoking `verify_api_parity.sh` (per VALIDATION.md per-task verification map for 03-03-T1: `grep -q 'ZEEKER_BASELINE_DIR.*phase-03-pre' scripts/verify_phase_03.sh`). The contract that `verify_api_parity.sh` honors that env var is now true.

**Wave 4 (Plan 04 — operator ship/no-ship gate) is also unblocked.** Plan 04's commands (`ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh`) now have well-defined semantics; without this plan, Plan 04 would invoke a script that errors out at line 17 because the hardcoded `phase-02` directory no longer exists.

**No blockers.** All static checks green; smoke test green; negative override green.

## Self-Check: PASSED

Verified before writing this SUMMARY:
- `scripts/capture_baseline.sh` exists at HEAD with `ZEEKER_BASELINE_DIR` at line 14: FOUND
- `scripts/verify_api_parity.sh` exists at HEAD with `ZEEKER_BASELINE_DIR` at line 10: FOUND
- Commit `5fd66ab` exists in `git log`: FOUND
- Commit `8445c43` exists in `git log`: FOUND
- `! grep -rn 'phase-02' scripts/` returns empty: CONFIRMED
- `bash -n` passes on both scripts: CONFIRMED
- Live-stack smoke test exit 0: CONFIRMED
- Negative override smoke test exit 1 + correct error message: CONFIRMED

---
*Phase: 03-flip-suffix-based-routing*
*Plan: 01*
*Completed: 2026-04-21*

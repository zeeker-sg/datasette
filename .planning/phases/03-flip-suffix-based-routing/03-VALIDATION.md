---
phase: 3
slug: flip-suffix-based-routing
status: shipped
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-21
updated: 2026-04-21
shipped: 2026-04-21
ship_decision: approved
ship_notes: "All 4 plans complete. verify_phase_03.sh exit 0 post-fix. verify_api_parity.sh exit 0 (12/12 clean). Phase-2 verifier checks #3 + #10 retired in same phase (operator-directed). Zero Category-D regressions. Live smoke: / → 404 frontend, /sglawwatch.json → 200 datasette, /frontend-test → 200 frontend, /sglawwatch HTML → 404 frontend (no zeeker-base.css fingerprint)."
---

# Phase 3 — Validation Strategy

> Per-phase validation contract. Phase 3 is a single-file Caddyfile edit + verifier-script adaptations. The risk surface is small but the failure modes are subtle (silent fallthrough). Almost all validation is shell + curl; no Python tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash + curl + jq + diff (no language test framework) |
| **Config file** | n/a (script-based assertions) |
| **Quick run command** | `bash scripts/verify_phase_03.sh` |
| **Full suite command** | `bash scripts/verify_phase_03.sh && ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh` |
| **Estimated runtime** | ~10 seconds (15-20 curl calls; no docker pulls or image builds) |

---

## Sampling Rate

- **After every task commit:** Run `bash scripts/verify_phase_03.sh`
- **After every plan wave:** Same (single wave per plan in this phase)
- **Before `/gsd-verify-work`:** Full suite green (verify_phase_03.sh + ZEEKER_BASELINE_DIR-parameterized verify_api_parity.sh)
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

> Populated by gsd-planner against actual plan task IDs. The 3 phase REQ-* IDs (REQ-suffix-routing-contract, REQ-api-byte-parity, REQ-incremental-migration) each map to at least one row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-T1 | 01 | 1 | REQ-incremental-migration | T-03-01 | scripts/capture_baseline.sh OUT_DIR honors ZEEKER_BASELINE_DIR env var with phase-03-pre default; no remaining hardcoded `phase-02` | shell | `bash -n scripts/capture_baseline.sh && grep -qE 'OUT_DIR="\$\{ZEEKER_BASELINE_DIR:-.*phase-03-pre\}"' scripts/capture_baseline.sh && ! grep -q 'phase-02' scripts/capture_baseline.sh` | ✅ planned | ⬜ pending |
| 03-01-T2 | 01 | 1 | REQ-incremental-migration | T-03-01, T-03-02, T-03-03 | scripts/verify_api_parity.sh BASELINE_DIR honors ZEEKER_BASELINE_DIR env var with phase-03-pre default; nonexistent override correctly fails fast with documented error | shell | `bash -n scripts/verify_api_parity.sh && grep -qE 'BASELINE_DIR="\$\{ZEEKER_BASELINE_DIR:-.*phase-03-pre\}"' scripts/verify_api_parity.sh && ! grep -q 'phase-02' scripts/verify_api_parity.sh && ZEEKER_BASELINE_DIR=/tmp/zeeker-no-such-dir-$$ bash scripts/verify_api_parity.sh 2>&1 \| grep -q "no baselines found"` | ✅ planned | ⬜ pending |
| 03-02-T1 | 02 | 2 | REQ-suffix-routing-contract, REQ-incremental-migration | T-03-02, T-03-03, T-03-07, T-03-09 | Caddyfile uses named `@datasette` matcher with both `path` lines (suffix list + `/-/*` prefix); matched-handler before catch-all in file order; passes `caddy validate`; commit modifies ONLY Caddyfile (single-file rollback) | shell | `docker run --rm -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && grep -qE '^\s*@datasette\s*\{' Caddyfile && grep -qE '^\s*path \*\.json \*\.csv \*\.db\s*$' Caddyfile && grep -qE '^\s*path /-/\*\s*$' Caddyfile && grep -qE '^\s*reverse_proxy @datasette zeeker-datasette:8001\s*$' Caddyfile && grep -qE '^\s*reverse_proxy frontend:8000\s*$' Caddyfile && [ "$(git show --stat HEAD \| grep -cE '^ [^\|]+\\\| ')" = "1" ] && git show --stat HEAD \| grep -qE '^ Caddyfile\s*\\\|'` | ✅ planned | ⬜ pending |
| 03-03-T1 | 03 | 3 | REQ-suffix-routing-contract, REQ-api-byte-parity | T-03-04, T-03-12, T-03-15, T-03-16 | scripts/verify_phase_03.sh exists + executable + bash -n valid + ≥100 lines + has check_positive/check_negative + body-content fallthrough sniff for `zeeker-base.css` + 11 negative-routing checks (incl. 3-segment row-URL shape) + Phase-2 verifier delegation + parity wrap with ZEEKER_BASELINE_DIR=phase-03-pre + does NOT restart caddy | shell | `test -x scripts/verify_phase_03.sh && bash -n scripts/verify_phase_03.sh && grep -q 'zeeker-base.css' scripts/verify_phase_03.sh && grep -q 'check_negative' scripts/verify_phase_03.sh && grep -q 'check_positive' scripts/verify_phase_03.sh && grep -q 'verify_phase_02.sh' scripts/verify_phase_03.sh && grep -q 'ZEEKER_BASELINE_DIR.*phase-03-pre' scripts/verify_phase_03.sh && grep -q 'verify_api_parity.sh' scripts/verify_phase_03.sh && [ "$(grep -c 'check_negative ' scripts/verify_phase_03.sh)" = "11" ] && [ "$(wc -l < scripts/verify_phase_03.sh)" -gt 100 ] && ! grep -q 'restart caddy' scripts/verify_phase_03.sh` | ✅ planned | ⬜ pending |
| 03-04-T1 | 04 | 4 | REQ-suffix-routing-contract, REQ-api-byte-parity | T-03-08, T-03-17, T-03-18, T-03-21 | After `docker compose restart caddy`: 3/3 services healthy; in-container Caddyfile contains `@datasette` (bind-mount picked up the new file); verify_phase_03.sh ran end-to-end with explicit exit code captured to forensic log; live stack reachable at http://localhost/-/versions.json | shell | `test -s .planning/phases/03-flip-suffix-based-routing/03-04-bringup-log.txt && grep -q 'docker compose restart caddy' .planning/phases/03-flip-suffix-based-routing/03-04-bringup-log.txt && grep -qE 'poll [0-9]+: 3/3 healthy' .planning/phases/03-flip-suffix-based-routing/03-04-bringup-log.txt && grep -qE '^exit code: [0-9]+' .planning/phases/03-flip-suffix-based-routing/03-04-bringup-log.txt && curl -fsS http://localhost/-/versions.json \| jq -e '.datasette' >/dev/null` | ✅ planned | ⬜ pending |
| 03-04-T2 | 04 | 4 | REQ-api-byte-parity | T-03-05, T-03-20 | Standalone verify_api_parity.sh log exists with exit code; 03-TEST-PLAN.md authored at CONTEXT-locked path with all 5 sections + Phase-2 four-category triage + rollback recipe | shell | `test -s .planning/phases/03-flip-suffix-based-routing/03-04-parity-log.txt && grep -q 'ZEEKER_BASELINE_DIR' .planning/phases/03-flip-suffix-based-routing/03-04-parity-log.txt && grep -qE '^exit code: [0-9]+' .planning/phases/03-flip-suffix-based-routing/03-04-parity-log.txt && test -f .planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md && grep -q 'docker compose restart caddy' .planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md && grep -q 'verify_phase_03.sh' .planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md && grep -q 'git revert' .planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md` | ✅ planned | ⬜ pending |
| 03-04-T3 | 04 | 4 | REQ-suffix-routing-contract, REQ-api-byte-parity, REQ-incremental-migration | T-03-05, T-03-06, T-03-19 | HUMAN CHECKPOINT: operator reads forensic logs + does manual visual smoke + replies ship/no-ship; SUMMARY documents decision + four-category triage; if ship → STATE/ROADMAP/REQUIREMENTS updated atomically; if no-ship → rollback executed and verified by verify_phase_02.sh against rolled-back stack | manual + shell | `test -f .planning/phases/03-flip-suffix-based-routing/03-04-SUMMARY.md && grep -qE 'ship\|no-ship' .planning/phases/03-flip-suffix-based-routing/03-04-SUMMARY.md` | ⏳ awaiting human | ⬜ pending |

---

## Wave 0 Requirements

These artifacts MUST exist before downstream waves can claim "done":

- [ ] `scripts/capture_baseline.sh` — already exists from Phase 2; needs ONE-LINE EDIT to honor `ZEEKER_BASELINE_DIR` env var (currently hardcodes `phase-02`). Change line 13: `OUT_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"`. **Plan 01 Task 1 covers this.**
- [ ] `scripts/verify_api_parity.sh` — same fix; line 10 hardcodes `phase-02`. **Plan 01 Task 2 covers this.**
- [ ] `scripts/verify_phase_03.sh` — NEW file; adapts `verify_phase_02.sh` pattern with positive-routing + negative-routing assertions. Includes body-content sniff guard against silent fallthrough (datasette HTML signature: `<link rel="stylesheet" href="/static/css/zeeker-base.css">` or table HTML rows). **Plan 03 Task 1 covers this.**
- [ ] `Caddyfile` — modified per **Plan 02 Task 1** (the actual routing flip; single-file commit).
- [x] `.planning/baselines/phase-03-pre/` — already exists from the post-Phase-2 re-baseline (commit `ee3f3ad`); 13 JSON + 13 .url files captured against the post-Caddy stack. No Wave-0 work needed beyond reading.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual confirmation that browser-loaded `http://localhost/` shows the FastAPI 404 (not the datasette HTML) | REQ-suffix-routing-contract | Browser rendering of frontend's default 404 vs datasette's "Database" page is the most decisive single user-visible signal | After Plan 04 Task 1 ships: open `http://localhost/` in a browser. Should see `{"detail":"Not Found"}` JSON or a plain text 404. Should NOT see the datasette homepage. **Plan 04 Task 3 (human checkpoint) explicitly requires this**; outcome documented in `03-04-SUMMARY.md`. |
| Production-overlay compatibility | REQ-incremental-migration | The Phase-3 Caddyfile must remain compatible with whatever Phase 4's production deploy does (TLS at `data.zeeker.sg`). Can't be tested locally. | Manual review by author when Phase 4 plans land: confirm Phase 4's `docker-compose.prod.yml` overlay (or equivalent) wraps the Phase-3 Caddyfile site block without rewriting it. RESEARCH Pattern 2 sketches the forward-compat shape. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (Plans 01-04 all include automated verify commands)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task in every plan has automated verify)
- [x] Wave 0 covers all MISSING references (script param edits in Plan 01 + verify_phase_03.sh in Plan 03 + Caddyfile in Plan 02)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter (planner sets this once Per-Task Verification Map is populated against actual plan task IDs)

**Approval:** approved by planner; gate runs at Plan 04 Task 3 with operator

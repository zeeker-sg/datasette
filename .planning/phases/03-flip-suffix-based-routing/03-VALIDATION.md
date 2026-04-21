---
phase: 3
slug: flip-suffix-based-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
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

> Will be populated by gsd-planner against actual plan task IDs. Below is the structural template the planner should fill. The 3 phase REQ-* IDs (REQ-suffix-routing-contract, REQ-api-byte-parity, REQ-incremental-migration) MUST each map to at least one row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-XX | 01 | 1 | REQ-incremental-migration | T-03-01 | scripts/capture_baseline.sh + scripts/verify_api_parity.sh accept ZEEKER_BASELINE_DIR env var so Phase-3+ can target their own baseline dirs | shell | `ZEEKER_BASELINE_DIR=/tmp/test bash -n scripts/capture_baseline.sh && grep -q 'ZEEKER_BASELINE_DIR' scripts/verify_api_parity.sh` | ❌ W0 | ⬜ pending |
| 03-02-XX | 02 | 2 | REQ-suffix-routing-contract | T-03-02, T-03-03 | Caddyfile uses named `@datasette` matcher with all four path predicates; matched-handler before catch-all (auto-sorted but written matched-first); validates clean | shell | `docker run --rm -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && grep -qE '^\s*@datasette' Caddyfile && grep -qE 'reverse_proxy frontend:8000' Caddyfile` | ❌ W0 | ⬜ pending |
| 03-03-XX | 03 | 3 | REQ-suffix-routing-contract, REQ-api-byte-parity | T-03-04 | scripts/verify_phase_03.sh exists + executable + valid syntax + asserts both positive routing (datasette) and negative routing (frontend 404 with body-content sniff for fallthrough) | shell | `test -x scripts/verify_phase_03.sh && bash -n scripts/verify_phase_03.sh && grep -q 'fallthrough\|datasette' scripts/verify_phase_03.sh` | ❌ W0 | ⬜ pending |
| 03-04-XX | 04 | 4 | REQ-suffix-routing-contract, REQ-api-byte-parity, REQ-incremental-migration | T-03-05, T-03-06 | After Caddyfile edit + caddy restart: verify_phase_03.sh exits 0; verify_api_parity.sh against phase-03-pre baselines exits 0; HTML routes (/, /sglawwatch) return 404 with frontend body, not datasette HTML | shell | `docker compose restart caddy && sleep 3 && bash scripts/verify_phase_03.sh && ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

These artifacts MUST exist before downstream waves can claim "done":

- [ ] `scripts/capture_baseline.sh` — already exists from Phase 2; needs ONE-LINE EDIT to honor `ZEEKER_BASELINE_DIR` env var (currently hardcodes `phase-02`). Change line 13: `OUT_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-02}"`. Plan 01 covers this.
- [ ] `scripts/verify_api_parity.sh` — same fix; line 10 hardcodes `phase-02`. Plan 01 covers this.
- [ ] `scripts/verify_phase_03.sh` — NEW file; adapts `verify_phase_02.sh` pattern with positive-routing + negative-routing assertions. Includes body-content sniff guard against silent fallthrough (datasette HTML signature: `<link rel="stylesheet" href="/static/css/zeeker-base.css">` or table HTML rows). Plan 03 covers this.
- [ ] `Caddyfile` — modified per Plan 02 (the actual routing flip).
- [ ] `.planning/baselines/phase-03-pre/` — already exists from the post-Phase-2 re-baseline (commit `ee3f3ad`); 13 JSON + 13 .url files captured against the post-Caddy stack. No Wave-0 work needed beyond reading.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual confirmation that browser-loaded `http://localhost/` shows the FastAPI 404 (not the datasette HTML) | REQ-suffix-routing-contract | Browser rendering of frontend's default 404 vs datasette's "Database" page is the most decisive single user-visible signal | After Plan 04 ships: open `http://localhost/` in a browser. Should see `{"detail":"Not Found"}` JSON or a plain text 404. Should NOT see the datasette homepage. Document outcome in `03-04-SUMMARY.md`. |
| Production-overlay compatibility | REQ-incremental-migration | The Phase-3 Caddyfile must remain compatible with whatever Phase 4's production deploy does (TLS at `data.zeeker.sg`). Can't be tested locally. | Manual review by author when Phase 4 plans land: confirm Phase 4's `docker-compose.prod.yml` overlay (or equivalent) wraps the Phase-3 Caddyfile site block without rewriting it. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (script param edits + verify_phase_03.sh)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter (planner sets this once Per-Task Verification Map is populated against actual plan task IDs)

**Approval:** pending

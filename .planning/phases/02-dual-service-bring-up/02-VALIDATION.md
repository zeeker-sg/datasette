---
phase: 2
slug: dual-service-bring-up
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Phase 2 is infrastructure-only (Docker Compose topology change + new placeholder service); the bulk of "validation" is shell/HTTP/Docker assertions, not unit tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (frontend Python) + bash assertions (compose/curl/parity scripts) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` (Wave 0 installs) |
| **Quick run command** | `bash scripts/verify_phase_02.sh` |
| **Full suite command** | `bash scripts/verify_phase_02.sh && cd packages/zeeker-frontend && uv run pytest -q` |
| **Estimated runtime** | ~30 seconds (compose health-poll dominates) |

---

## Sampling Rate

- **After every task commit:** Run `bash scripts/verify_phase_02.sh` (compose ps + healthcheck assertions; ~10s)
- **After every plan wave:** Run full suite (verify_phase_02.sh + frontend pytest)
- **Before `/gsd-verify-work`:** Full suite green + `bash scripts/verify_api_parity.sh` green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Will be populated by gsd-planner against the plan task IDs. Below is the structural template the planner should fill, with one row per task. The five locked phase requirements (REQ-incremental-migration, REQ-internal-only-datasette-exposure, REQ-frontend-data-via-http, REQ-preserve-zeeker-cli, REQ-api-byte-parity) MUST each map to at least one row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | REQ-api-byte-parity | — | Baseline JSON captured before any compose mutation | shell | `bash scripts/capture_baseline.sh` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | REQ-api-byte-parity | — | Parity-verifier script exists and is idempotent | shell | `test -x scripts/verify_api_parity.sh` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | REQ-api-byte-parity | — | Phase-2 verifier script exists | shell | `test -x scripts/verify_phase_02.sh` | ❌ W0 | ⬜ pending |
| 02-02-XX | 02 | 1 | REQ-frontend-data-via-http | — | Frontend container has no sqlite3 binary, no `./data` mount | shell | `docker compose run --rm frontend sh -c '! command -v sqlite3'` && `docker compose config | grep -A2 frontend | grep -v "./data"` | ❌ W0 | ⬜ pending |
| 02-03-XX | 03 | 2 | REQ-internal-only-datasette-exposure | — | Datasette service has no `ports:` mapping; only Caddy publishes ports | shell | `docker compose config --services-with-ports | grep -v caddy | wc -l | xargs -I{} test {} -eq 0` | ❌ W0 | ⬜ pending |
| 02-04-XX | 04 | 2 | REQ-incremental-migration | — | All three services healthy after `docker compose up -d` | shell | `docker compose ps --format json | jq -r '.[] | .Health' | sort -u | tr -d '\n' | grep -qx healthy` | ❌ W0 | ⬜ pending |
| 02-05-XX | 05 | 3 | REQ-api-byte-parity | — | Post-deploy parity diff is empty (modulo volatile fields) | shell | `bash scripts/verify_api_parity.sh` | ❌ W0 | ⬜ pending |
| 02-06-XX | 06 | 3 | REQ-preserve-zeeker-cli | — | `zeeker` CLI invocation against the post-deploy stack still resolves and returns successfully | shell | `command -v zeeker && zeeker --help >/dev/null` (full deploy smoke is manual — see Manual-Only) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `scripts/capture_baseline.sh` — captures JSON for the canonical URL set BEFORE the compose mutation; commits baselines to `.planning/baselines/phase-02/`
- [ ] `scripts/verify_api_parity.sh` — diffs current responses against baselines with the agreed `jq` strip filter (volatile fields: `query_ms`, `__time__`, datasette `version`)
- [ ] `scripts/verify_phase_02.sh` — wraps the assertions from the per-task map (compose ps, healthcheck status, ports inventory, no-sqlite-in-frontend)
- [ ] `packages/zeeker-frontend/pyproject.toml` — pytest declared as dev dep
- [ ] `packages/zeeker-frontend/tests/conftest.py` — shared fixtures (TestClient for the FastAPI app)
- [ ] `packages/zeeker-frontend/tests/test_health.py` — `GET /frontend-test → 200, body == {"status":"ok","service":"zeeker-frontend"}`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end production deploy via `zeeker deploy` against post-Phase-2 stack | REQ-preserve-zeeker-cli | Touches S3 + production infra; cannot automate in a Phase-2 plan run | After Phase-2 ships locally, run `zeeker deploy` against the staging environment with one test database; confirm push succeeds and a refresh cycle picks up the new database. Document outcome in `02-SUMMARY.md`. |
| TLS certificate provisioning (auto-HTTPS at `data.zeeker.sg`) | — (deferred to Phase 3) | Production-only; not in scope for this phase | N/A this phase |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (capture_baseline, verify_api_parity, verify_phase_02, frontend pytest scaffolding)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (planner sets this once Per-Task Verification Map is fully filled in against the actual plan tasks)

**Approval:** pending

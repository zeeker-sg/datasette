---
phase: 2
slug: dual-service-bring-up
status: shipped
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-20
updated: 2026-04-21
shipped: 2026-04-21
ship_decision: approved
ship_notes: "All 5 plans complete. verify_phase_02.sh exit 1 and verify_api_parity.sh exit 1 both triaged as non-regressions: (a) localhost:8001 → localhost host-base-URL drift in next_url/toggle_url is invisible in production where hostname is data.zeeker.sg both pre- and post-Phase-2; (b) S3 metadata refresh + datasette 0.65.1→0.65.2 + daily zeeker-judgements row import drift are environmental and would have happened without the topology change. Zero topology-induced API regressions. Row counts identical (10/10) on direct comparison. Re-baseline against post-Caddy stack recommended before Phase 3 starts."
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Phase 2 is infrastructure-only (Docker Compose topology change + new placeholder service); the bulk of "validation" is shell/HTTP/Docker assertions, not unit tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (frontend Python) + bash assertions (compose/curl/parity scripts) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` (landed by plan 02) |
| **Quick run command** | `bash scripts/verify_phase_02.sh` |
| **Full suite command** | `bash scripts/verify_phase_02.sh && cd packages/zeeker-frontend && uv run pytest -q` |
| **Estimated runtime** | ~30 seconds (compose health-poll dominates) |

---

## Sampling Rate

- **After every task commit:** Run `bash scripts/verify_phase_02.sh` (compose ps + healthcheck assertions; ~10s). For tasks within plan 02 (frontend scaffolding), also run `cd packages/zeeker-frontend && uv run pytest -q` (~2s).
- **After every plan wave:** Run full suite (verify_phase_02.sh + frontend pytest).
- **Before `/gsd-verify-work`:** Full suite green + `bash scripts/verify_api_parity.sh` green.
- **Max feedback latency:** 30 seconds.

---

## Per-Task Verification Map

> Populated against the actual plan task IDs. All five locked phase requirements (REQ-incremental-migration, REQ-internal-only-datasette-exposure, REQ-frontend-data-via-http, REQ-preserve-zeeker-cli, REQ-api-byte-parity) each map to at least one row. Wave numbering here uses 0-indexed waves as the orchestrator's briefing described (Wave 0 = sequential prereqs, Wave 1+2 = parallel, Wave 3 = final sequential). Plan `wave:` frontmatter uses 1-indexed (Wave 1 / Wave 2 / Wave 3 / Wave 4). Both describe the same ordering; see the map header.

| Task ID | Plan | Wave (1-idx) | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | REQ-api-byte-parity | T-02-02 | Baseline JSON captured BEFORE any compose mutation | shell | `test -x scripts/capture_baseline.sh && ls .planning/baselines/phase-02/*.json \| head -1` | ✅ in plan | ⬜ pending |
| 02-01-02 | 01 | 1 | REQ-api-byte-parity, REQ-internal-only-datasette-exposure, REQ-frontend-data-via-http, REQ-incremental-migration | T-02-04 | Parity verifier + phase-2 verifier scripts exist, executable, syntax-valid; capture_baseline.sh emits `.url` sidecars | shell | `test -x scripts/verify_api_parity.sh && test -x scripts/verify_phase_02.sh && bash -n scripts/verify_api_parity.sh && bash -n scripts/verify_phase_02.sh` | ✅ in plan | ⬜ pending |
| 02-01-03 | 01 | 1 | REQ-api-byte-parity | T-02-02 | Human-verified baselines are non-empty and match the pre-mutation stack's datasette version | human-checkpoint | Human approves "approved" after inspecting `.planning/baselines/phase-02/` | ✅ in plan | ⬜ pending |
| 02-02-01 | 02 | 2 | REQ-frontend-data-via-http, REQ-incremental-migration | T-02-06, T-02-10 | Frontend package installs cleanly with uv; pytest green; no sqlite/datasette deps in pyproject.toml or uv.lock | shell | `cd packages/zeeker-frontend && uv run pytest -q` | ✅ in plan | ⬜ pending |
| 02-02-02 | 02 | 2 | REQ-frontend-data-via-http | T-02-06 | Frontend Dockerfile builds; built image has no sqlite3 binary; image serves /frontend-test standalone | shell | `docker build -t zeeker-frontend:phase-02-test packages/zeeker-frontend/ && docker run --rm --entrypoint sh zeeker-frontend:phase-02-test -c '! command -v sqlite3'` | ✅ in plan | ⬜ pending |
| 02-03-01 | 03 | 2 | REQ-incremental-migration, REQ-internal-only-datasette-exposure | T-02-11, T-02-12 | Caddyfile exists, validates via `caddy validate`, uses `zeeker-datasette:8001` (not placeholder `datasette`), has `auto_https off`, admin bound to localhost:2019 | shell | `docker run --rm -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` | ✅ in plan | ⬜ pending |
| 02-04-01 | 04 | 3 | REQ-internal-only-datasette-exposure, REQ-frontend-data-via-http, REQ-incremental-migration, REQ-preserve-zeeker-cli, REQ-api-byte-parity | T-02-16..T-02-22 | docker-compose.yml validates; three services; datasette has no ports; frontend has no volumes + empty env (beyond PYTHONUNBUFFERED); caddy publishes only 80/443; depends_on uses service_healthy | shell | `docker compose config -q && docker compose config --services-with-ports \| tr '\n' ' ' \| grep -Eq '^\s*caddy\s*$'` | ✅ in plan | ⬜ pending |
| 02-05-01 | 05 | 4 | REQ-internal-only-datasette-exposure, REQ-frontend-data-via-http, REQ-incremental-migration | T-02-23, T-02-25 | Three-service stack comes up healthy; verify_phase_02.sh exits 0 | shell | `bash scripts/verify_phase_02.sh` | ✅ in plan | ⬜ pending |
| 02-05-02 | 05 | 4 | REQ-api-byte-parity | T-02-24 | Post-Caddy responses match pre-mutation baselines; verify_api_parity.sh exits 0 | shell | `bash scripts/verify_api_parity.sh` | ✅ in plan | ⬜ pending |
| 02-05-03 | 05 | 4 | REQ-preserve-zeeker-cli, REQ-incremental-migration, all REQ-* | T-02-27 | Human ship/no-ship decision recorded in 02-05-SUMMARY.md; 02-VALIDATION.md marked nyquist_compliant | human-checkpoint | Human approves "ship" after reading both logs + eyeballing live stack | ✅ in plan | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement coverage check

| Requirement | Rows covering it |
|-------------|------------------|
| REQ-api-byte-parity | 02-01-01, 02-01-02, 02-01-03, 02-04-01, 02-05-02, 02-05-03 |
| REQ-internal-only-datasette-exposure | 02-01-02, 02-03-01, 02-04-01, 02-05-01, 02-05-03 |
| REQ-frontend-data-via-http | 02-01-02, 02-02-01, 02-02-02, 02-04-01, 02-05-01, 02-05-03 |
| REQ-incremental-migration | 02-01-02, 02-02-01, 02-03-01, 02-04-01, 02-05-01, 02-05-03 |
| REQ-preserve-zeeker-cli | 02-04-01 (no accidental mutation of datasette service surface), 02-05-03 (zeeker --help smoke + manual deploy noted in SUMMARY) |

All five locked phase requirements are covered by at least two rows each. ✅

---

## Wave 0 Requirements

These artifacts MUST exist before downstream waves can claim "done":

- [ ] `scripts/capture_baseline.sh` — captures JSON for the canonical URL set BEFORE the compose mutation; commits baselines to `.planning/baselines/phase-02/`. Landed by plan 01, task 1.
- [ ] `scripts/verify_api_parity.sh` — diffs current responses against baselines with the agreed `jq` strip filter (volatile fields: `query_ms`, `__time__`, `request_duration_ms`; `/-/versions.json` diffed structurally on `keys`). Landed by plan 01, task 2.
- [ ] `scripts/verify_phase_02.sh` — wraps every assertion from the Per-Task Verification Map (compose ps, healthcheck status, ports inventory, no-sqlite-in-frontend, no /data mount, caddy DNS resolves zeeker-datasette). Landed by plan 01, task 2.
- [ ] `.planning/baselines/phase-02/*.json` + matching `*.url` sidecars — committed pre-mutation baselines. Landed by plan 01, task 1.
- [ ] `packages/zeeker-frontend/pyproject.toml` — pytest declared as dev dep. Landed by plan 02, task 1.
- [ ] `packages/zeeker-frontend/tests/conftest.py` — TestClient fixture. Landed by plan 02, task 1.
- [ ] `packages/zeeker-frontend/tests/test_frontend.py` — `GET /frontend-test → 200 + correct body`, unknown path → 404, module-level sqlite3 fence. Landed by plan 02, task 1.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end production deploy via `zeeker deploy` against post-Phase-2 stack | REQ-preserve-zeeker-cli | Touches S3 + production infra; cannot automate in a Phase-2 plan run | After Phase-2 ships locally, run `zeeker deploy` against the staging environment with one test database; confirm push succeeds and a refresh cycle picks up the new database. Document outcome in `02-05-SUMMARY.md`. |
| TLS certificate provisioning (auto-HTTPS at `data.zeeker.sg`) | — (deferred) | Production-only; not in scope for this phase (Phase 2 is local-HTTP only; production overlay in a later phase) | N/A this phase |
| Browser eyeball of the live stack at http://localhost/ | REQ-incremental-migration | Visual confirmation that site behavior is unchanged from user perspective | Open http://localhost/ in a browser; confirm the current Datasette homepage renders as expected. Noted in 02-05-SUMMARY.md. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (every task in plans 01–05 has either a shell automated command or a human-checkpoint gate backed by shell-verifiable evidence)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (each plan has at most 2 tasks between verify-able gates; task 3 of plan 01 is a checkpoint following two automated tasks)
- [x] Wave 0 covers all MISSING references (capture_baseline, verify_api_parity, verify_phase_02, frontend pytest scaffolding) — landed by plans 01 and 02
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved-for-execute

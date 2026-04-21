---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-21T10:06:00.000Z"
progress:
  total_phases: 7
  completed_phases: 1
  total_plans: 9
  completed_plans: 7
  percent: 78
---

## Phase 2: Dual-service bring-up — SHIPPED 2026-04-21

**Outcome:** Three-service Docker topology (datasette internal-only + frontend FastAPI placeholder + caddy reverse proxy) is live locally. All 5 plans complete; verifier scripts both red on triage-grade non-regressions (host-base-URL drift, S3 metadata refresh, datasette 0.65.1→0.65.2, daily import drift). Zero topology-induced API regressions. See `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md`.

**Live stack:**

- caddy: `:80`/`:443` public — only service exposed
- zeeker-datasette: internal only at `zeeker-datasette:8001` (no host port mapping)
- frontend: internal only at `frontend:8000` — `/frontend-test` returns `{"status":"ok","service":"zeeker-frontend"}`; Caddy correctly 404s on it externally (Phase-3 forward-compat preserved)

**Recommended before Phase 3:** Re-baseline against the post-Caddy stack so Phase 3's suffix-routing flip has a stable comparison point. The current baselines at `.planning/baselines/phase-02/` reference the pre-mutation `localhost:8001` stack and will produce noisy URL-host diffs in any future verification.

**Next phase:** Phase 3 — Flip suffix-based routing (`*.json|*.csv|*.db|/-/* → datasette`, else → frontend). Depends on Phase 2 (this).

## Phase 2 plan completion

- 02-01 SHIPPED — Wave-0 verifier scripts + 13 pre-mutation baselines committed (`efdd3d5`, `4036226`)
- 02-02 SHIPPED — `packages/zeeker-frontend/` FastAPI scaffold + Dockerfile + pytest (`b536f64`, `7deab3f`)
- 02-03 SHIPPED — root `Caddyfile` (transparent proxy → `zeeker-datasette:8001`, auto_https off) (`0b40b86`)
- 02-04 SHIPPED — `docker-compose.yml` rewrite to three-service topology (single-file commit, `git revert b2a20a0` is rollback) (`b2a20a0`)
- 02-05 SHIPPED — Local bring-up + verify_phase_02.sh + verify_api_parity.sh + ship/no-ship checkpoint approved by user

**Planned Phase:** 3 (Flip suffix-based routing) — 4 plans — 2026-04-21T07:33:59.303Z

## Phase 3 plan completion

- 03-01 SHIPPED 2026-04-21 — Verifier scripts parameterized via `ZEEKER_BASELINE_DIR` env var (default `.planning/baselines/phase-03-pre/`). `scripts/capture_baseline.sh` (`5fd66ab`) + `scripts/verify_api_parity.sh` (`8445c43`); 12/12 byte-parity smoke test PASS against live post-Phase-2 stack; negative override fails fast as designed. No `phase-02` substring remains in `scripts/`. Plan 02 (Caddyfile flip), Plan 03 (verify_phase_03.sh), and Plan 04 (operator gate) all unblocked.
- 03-02 SHIPPED 2026-04-21 — Caddyfile flipped from transparent reverse_proxy to named `@datasette` matcher router (`*.json|*.csv|*.db|/-/* → zeeker-datasette:8001`, catch-all → `frontend:8000`); validated via Docker-one-shot `caddy validate`; single-file commit `ebf3f52` (1 file changed, 36 insertions, 29 deletions). Caddy NOT restarted — live container still on Phase-2 transparent-proxy config (intentional; Plan 04 owns the restart + verifier-run gate). REQ-suffix-routing-contract on-disk; REQ-incremental-migration single-file rollback discipline verified. `caddy fmt --overwrite` applied for tab-indent consistency.

## Phase 3 decisions accumulated

- Parameterize phase-scoped paths via env-var-with-default pattern (`${VAR:-default}`) rather than re-hardcoding per phase. Default points to current-phase directory so no-args invocation is always safe; downstream phases override via `export ZEEKER_BASELINE_DIR=...` before invoking. Locked in 03-CONTEXT D-XX (option b).
- JQ_STRIP filter is the bright line between honest verification and rationalization. Phase 3 inherits Phase 2's discipline: NEVER widen the filter to mask diffs. Triage stays at the human checkpoint (Plan 04).
- Named matcher `@datasette` (not `@datasette_api`); two `path` lines OR'd inside the matcher (suffix list + `/-/*` prefix on separate lines for legibility); matched-handler before catch-all in file order (Caddy auto-sorts no-matcher last regardless). No snippet refactor (`(api-routes)` + `import`); no static-asset `respond` short-circuits — both deferred per CONTEXT D-XX. Locked in 03-02 commit.
- Validate-but-don't-restart split: Plan 02 mutates+validates the on-disk Caddyfile; Plan 04 owns `docker compose restart caddy` + verifier-run as one atomic gate (per RESEARCH Pattern 4 / Pitfall 2 — `restart` sidesteps bind-mount inode-swap issues that affect `caddy reload`).

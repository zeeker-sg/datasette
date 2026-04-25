---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-25T13:30:27.644Z"
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 20
  completed_plans: 19
  percent: 95
---

## Phase 3: Flip suffix-based routing — SHIPPED 2026-04-21

**Outcome:** Suffix-based routing is LIVE. `*.json`, `*.csv`, `*.db`, and `/-/*` route to datasette; everything else routes to frontend. Frontend currently only serves `/frontend-test` (200) and 404s on all HTML routes — Phase 4+ fill in the real HTML routes. `verify_phase_03.sh` exit 0; `verify_api_parity.sh` against `phase-03-pre/` exit 0 (12/12 byte-parity clean). Zero Category-D regressions.

**Also retired Phase-2 stale checks during this phase** (per operator request):

- `verify_phase_02.sh` check #3: jq filter widened to exclude EXPOSE-only Publishers entries (`PublishedPort: 0`)
- `verify_phase_02.sh` check #10: polarity inverted from "expects 404 from datasette via Caddy" to "expects 200 from frontend via Caddy" — the new assertion matches Phase-3 semantics

**Live stack (unchanged topology from Phase 2; only Caddy config rewritten):**

- caddy `:80`/`:443` (public, only service exposed) — now routing by suffix
- zeeker-datasette internal only at `zeeker-datasette:8001`
- frontend internal only at `frontend:8000`

**Rollback:** `git revert ebf3f52 && docker compose restart caddy` (single-commit rollback for the Caddyfile flip).

**Next phase:** Phase 4 — Port home + database pages (`/` and `/{db}` routes in FastAPI/Jinja; first phase that ships a user-visible HTML change; first phase that deploys to production).

## Phase 3 plan completion

- 03-01 SHIPPED — Verifier scripts parameterized via `ZEEKER_BASELINE_DIR` (default `phase-03-pre`) (`5fd66ab`, `8445c43`)
- 03-02 SHIPPED — Caddyfile flipped to named `@datasette` matcher (single-file commit `ebf3f52` — rollback target)
- 03-03 SHIPPED — `scripts/verify_phase_03.sh` authored with 7 positive + 11 negative routing checks + body-content fallthrough sniff (`5f9a224`)
- 03-04 SHIPPED — Caddy restarted, verifiers ran, operator approved ship + retire-stale-checks

## Phase 3 decisions accumulated

- **Parameterize phase-scoped paths via env var with default** (`${VAR:-default}`). Pattern reusable for Phase 4+ without re-hardcoding.
- **JQ_STRIP filter discipline:** never widen to mask diffs; triage stays at human checkpoints.
- **Matched-handler before catch-all** in Caddyfile (readability; Caddy auto-sorts anyway).
- **Validate-but-don't-restart split:** plan that mutates file ≠ plan that restarts service; restart belongs to the verifier-run plan (RESEARCH Pitfall 2 — bind-mount inode-swap).
- **Fingerprint-sniff over status codes** — `zeeker-base.css` (datasette HTML) vs `"detail":"Not Found"` (frontend 404). The sole reliable signal for silent-fallthrough detection.
- **Verifier composition over duplication:** Phase-N verifier delegates to Phase-(N-1) verifier for inherited topology invariants.
- **Stale-check retirement in same phase** — if a Phase-(N-1) sentinel's polarity flips by Phase-N's design, retire it in Phase N rather than defer. Operator's call on this one; locked for future phases too.

## Phase 2: Dual-service bring-up — SHIPPED 2026-04-21

**Outcome:** Three-service Docker topology (datasette internal-only + frontend FastAPI placeholder + caddy reverse proxy). All 5 plans complete. See `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md`.

- 02-01 SHIPPED — Wave-0 verifier scripts + 13 pre-mutation baselines (`efdd3d5`, `4036226`)
- 02-02 SHIPPED — `packages/zeeker-frontend/` FastAPI scaffold + Dockerfile + pytest (`b536f64`, `7deab3f`)
- 02-03 SHIPPED — root `Caddyfile` (`0b40b86`)
- 02-04 SHIPPED — `docker-compose.yml` three-service rewrite (single-file commit, `git revert b2a20a0` is rollback)
- 02-05 SHIPPED — Local bring-up + verifiers + ship checkpoint approved

**Planned Phase:** 5 (port-table-browse-row-view) — 5 plans — 2026-04-25T06:28:28.024Z

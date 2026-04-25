# Phase 5 — Deploy Notes

**Authored:** 2026-04-25
**Operator decision required:** ship-or-no-ship checkpoint at end of Plan 05-05 Task 4.

## Phase-4 deploy deferral — carry-forward

Phase 4 (`/` and `/{db}` HTML routes) shipped locally on 2026-04-21 but the production deploy
was DEFERRED at the end of Plan 04-05 per operator decision. The deferral rationale captured
in `04-05-SUMMARY.md`: ship a local-only Phase-4 + Phase-5 combo so the editorial UX is end-to-end
coherent before public eyes see it (avoids a one-day window where `/{db}/{table}` routes 404
while `/` looks polished).

## Phase 5 deploy decision — operator's call at the end of this plan

Three options the operator may take after `verify_phase_05.sh` exits 0:

1. **Ship Phase 4 + 5 together to production.**
   - Run `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` per `04-05-DEPLOY.md`.
   - Run `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_05.sh` immediately after.
   - On any A/B regression, revert per `04-05-DEPLOY.md` three-layer rollback runbook.

2. **Continue deferring deploy.** Most likely path if any of the following are true:
   - Phase 6 auxiliary routes (developers / status / sources / about / how-to-use / llms.txt /
     /-/search / /-/sql) are imminent and operator wants them in the same deploy.
   - Visual review against sketch-findings reveals additional polish needed (e.g. font-size
     tuning, drop-cap suppression on short bodies, longform spacing).
   - API parity drifted in section O against `phase-03-pre` baselines and triage not yet done.
   - Operator simply wants more soak time on the local stack.

3. **Partial ship — Phase-4 only.** Skip Phase-5 routes in production until Phase 6 is also
   ready. This requires a Caddy/router toggle that's out of scope for Phase 5 (Phase 5 ships
   all-or-nothing on the frontend service). NOT recommended.

## Pre-checkpoint operator checklist

- [ ] All 5 Phase-5 plans complete; `cd packages/zeeker-frontend && uv run pytest -q` exits 0
      (full suite green, ~80+ tests after this phase lands)
- [ ] `docker compose up -d --build` brings local stack green; healthcheck on
      `http://localhost/-/versions.json` returns 200
- [ ] `bash scripts/verify_phase_05.sh` exits 0
- [ ] Manual visual sweep on `http://localhost`:
      - [ ] `/sglawwatch/headlines` (feed mode) — sketch 004-A parity
      - [ ] `/sglawwatch/headlines/<pk>` (article mode) — sketch 003-A parity
      - [ ] `/Zeeker-Judgements/judgments` (tabular mode)
      - [ ] `/Zeeker-Judgements/judgments/<pk>` (judgment mode) — sketch 003-B parity
      - [ ] `/sglawwatch/about_singapore_law` (longform-list)
      - [ ] `/sglawwatch/about_singapore_law/<pk>` (longform mode)
- [ ] Triage any verifier failures using the Phase-2 four-category triage:
      - **A. Real regression:** investigate; do NOT ship.
      - **B. Triage-acceptable drift:** environmental (datasette version, daily import drift,
            S3 metadata refresh); ship if isolated.
      - **C. Stale check:** the assertion no longer matches Phase-5 design; retire in this
            phase (do NOT defer).
      - **D. Cosmetic:** ship; track in next phase.

## Ship checkpoint outcome

| Field | Value |
|-------|-------|
| Date / time | 2026-04-25 ~16:00 SGT |
| Decision (1, 2, 3) | **2 — continue deferring deploy** (with stale-check retirement) |
| verify_phase_05.sh exit code | 1 (failures all in Phase-2 check #11 delegation; zero failures in Phase-5-specific sections) |
| Failed assertions (if any) | `verify_api_parity.sh` (all 6 byte-diff fails — `/-/metadata.json`, `/sg-gov-newsrooms/_zeeker_schemas.json`, `/sg-gov-newsrooms/_zeeker_updates.json`, `/sg-gov-newsrooms.json`, `/sglawwatch/about_singapore_law.json`, `/sglawwatch/headlines.json`) |
| Triage category for each failure | All **C — stale check** (intentional metadata.json content evolution since `phase-03-pre/` baseline capture: Phase-4 platform branding rewrite + Phase-5 `display.*` blocks; pre-edit metadata at commit `4f79811^` already had the live branding) plus a few **B — env drift** (timestamps + counts in `_zeeker_updates`/`sg-gov-newsrooms`) — zero Category-A regressions |
| Rollback executed? | No |
| STATE.md / ROADMAP.md updated? | Yes (after retirement commit) |

### Action taken

`verify_phase_02.sh` check #11 (`REQ-api-byte-parity` invoking `verify_api_parity.sh`) was retired at the Phase-5 boundary, following the locked Phase-3 decision recorded in `STATE.md`: *"Stale-check retirement in same phase — if a Phase-(N-1) sentinel's polarity flips by Phase-N's design, retire it in Phase N rather than defer."* Same pattern as Phase-3's retirement of Phase-2 checks #3 and #10.

`scripts/verify_api_parity.sh` is preserved on disk; future phases that want byte-parity guarantees can capture a fresh `phase-N-pre/` baseline first and re-point the script.

**Production deploy of Phase-4 + Phase-5 continues to be deferred** (option 2). Justification carries forward from Plan 04-05's deferral: ship-when-Phase-6-is-ready so the editorial UX is end-to-end coherent before public users see it.

## References

- Phase 4 deploy runbook: `.planning/phases/04-port-home-database-pages/04-05-DEPLOY.md` (still valid for Phase 5; same docker-compose.prod.yml + Caddyfile.prod)
- Phase 4 ship summary: `.planning/phases/04-port-home-database-pages/04-05-SUMMARY.md`
- Phase-2/3/4 four-category triage: established in `02-05-SUMMARY.md`, evolved in `03-04-SUMMARY.md`
- Verifier: `scripts/verify_phase_05.sh`
- API parity: `scripts/verify_api_parity.sh` against `.planning/baselines/phase-03-pre/`

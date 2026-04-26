# Phase 4 — Production deploy runbook

**Status:** authored by Plan 04-05 before the deploy runs.

## Pre-deploy checklist (local)

1. Plans 04-01 through 04-04 merged.
2. `cd packages/zeeker-frontend && uv run pytest -v` green.
3. Local stack healthy: `docker compose ps` shows all three services healthy.
4. `bash scripts/verify_phase_04.sh` exits 0 against localhost.
5. `ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh` exits 0 (12/12).

If ANY of the above fails, STOP. Don't deploy.

## Deploy recipe

```bash
# 1) From dev machine — commit + push everything
git status   # must be clean
git push

# 2) SSH to production host
ssh <prod-host>
cd /path/to/zeeker-datasette

# 3) Snapshot the current image tag for rapid rollback (before pulling)
docker image tag zeeker-datasette-frontend:latest zeeker-datasette-frontend:pre-phase-04 || true

# 4) Pull + rebuild
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 5) Wait for healthchecks (S3 download + container start)
sleep 30
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 6) Production smoke
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh
```

## Human checkpoint — ship / no-ship triage

Use the **Phase-2 four-category triage** (same pattern used in 02-05 and 03-04):

| Category | Definition | Action |
|---|---|---|
| **A — Green** | Verifier all green; home/database pages look right per sketch-skill contract; no user reports in first 10 min. | **SHIP**. Continue to post-ship steps. |
| **B — Cosmetic** | Verifier green but visual bug (e.g., font lagging, card accent wrong, stat number misaligned). | **SHIP** (fix in next phase or patch plan). Document in SUMMARY. |
| **C — Functional but non-blocking** | One secondary assertion fails (e.g., font 200 via localhost but 304 via TLS). Investigate; most 304s are success. | **SHIP** after confirming it's a non-regression. |
| **D — Regression** | Parity verifier fails on previously-green URL, OR hidden tables leak, OR 500s on core routes, OR `.json` surface broken. | **NO-SHIP — ROLLBACK IMMEDIATELY**. |

## Post-ship steps (if shipped)

1. Update STATE.md — `status: phase-4-complete`, bump `completed_phases`, etc.
2. Update ROADMAP.md — mark Phase 4 plans `[x]`, add SHIPPED line.
3. Capture `phase-04-pre` baselines for Phase-5 reference (only AFTER prod is confirmed stable — typically 1h soak):
   ```bash
   # From a machine that can reach prod
   ZEEKER_BASELINE_DIR=.planning/baselines/phase-04-pre bash scripts/capture_baseline.sh
   git add .planning/baselines/phase-04-pre
   git commit -m "chore: capture phase-04-pre baselines"
   ```
4. Commit STATE/ROADMAP atomically: `git commit -m "docs(04): phase 4 SHIPPED"`.

## Rollback (if D-regression)

Two rollback layers, try in order:

**Layer 1 — Revert the deploy commit (recommended):**
```bash
ssh <prod-host>
cd /path/to/zeeker-datasette
git log -n 5 --oneline   # find the Phase-4 deploy commit
git revert <deploy-sha>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
sleep 30
BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_03.sh   # Phase-3 surface should be green
```

**Layer 2 — Re-tag the snapshot image (emergency, only if Layer 1 fails):**
```bash
ssh <prod-host>
docker image tag zeeker-datasette-frontend:pre-phase-04 zeeker-datasette-frontend:latest
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Layer 3 — Revert Phase-3 too (catastrophic — ONLY if both above fail):**
```bash
# Revert to pre-M2 fully-datasette topology. Use git log to find the Phase-3 Caddyfile commit,
# then revert that too. This is not expected to be needed; document and escalate.
```

After rollback, update STATE.md with the `no-ship` category-D outcome and the actual regression observed.

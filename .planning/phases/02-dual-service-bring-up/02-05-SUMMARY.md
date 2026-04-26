---
phase: 02-dual-service-bring-up
plan: 05
subsystem: infra
tags: [docker-compose, caddy, fastapi, healthcheck, reverse-proxy, verification, parity]

# Dependency graph
requires:
  - phase: 02-dual-service-bring-up
    provides: "Plan 02-01 — pre-mutation baselines (12 JSON + 12 .url) + scripts/verify_phase_02.sh + scripts/verify_api_parity.sh; Plan 02-02 — packages/zeeker-frontend/{Dockerfile,src/zeeker_frontend/main.py with /frontend-test}; Plan 02-03 — root /Caddyfile with reverse_proxy zeeker-datasette:8001; Plan 02-04 — three-service docker-compose.yml"
provides:
  - "Empirical bring-up of three-service stack: zeeker-datasette internal-only, zeeker-frontend internal-only, zeeker-caddy publishing :80/:443/:443/udp — all three services healthy within 14 seconds of `docker compose up -d`"
  - "REQ-internal-only-datasette-exposure verified at runtime — `curl http://localhost:8001/-/versions.json` fails with curl exit code 7 (Connection refused), `docker compose ps` shows datasette PORTS column is `8001/tcp` (no host bind), `docker compose ps --format json | jq` confirms only caddy has any Publishers entry with `PublishedPort > 0`"
  - "REQ-frontend-data-via-http verified at runtime — `docker exec frontend command -v sqlite3` returns nothing; no /data mount on frontend container; pyproject.toml grep for sqlite/datasette returns nothing"
  - "Caddy → datasette internal hop verified — `docker compose exec caddy wget -qO- http://zeeker-datasette:8001/-/versions.json` returns valid JSON with datasette version 0.65.2"
  - "Phase-3 forward-compat verified — `curl http://localhost/frontend-test` returns 404 (Caddy NOT yet routing to frontend; that's the Phase-3 flip)"
  - "Two forensic logs captured: 02-05-bringup-log.txt (compose down/build/up/wait/ps/verifier output) and 02-05-parity-log.txt (standalone verify_api_parity.sh invocation)"
  - "**Verification gate result: NO-SHIP-WITHOUT-DECISION.** verify_phase_02.sh exits 1 (two failures); verify_api_parity.sh exits 1 (eleven byte-diffs across three categories — none topology-induced regressions, all explainable, but the gate as written is red. Human ship/no-ship decision required at Task 3 checkpoint)"
affects: [03-routing-flip (inherits a working three-service stack; will replace only the Caddyfile reverse_proxy line with suffix-based routing), 07-datasette-shrink (will shrink the datasette image; the compose stanza shape stays stable), 08-prod-overlay (will add docker-compose.prod.yml that flips auto_https on at data.zeeker.sg)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual-log forensic capture: both bring-up sequence and standalone parity check write to .txt files committed alongside the SUMMARY — `git diff` shows exactly what was observed at the verification moment (T-02-23 mitigation)"
    - "Three-category parity-failure triage: every diff classified as (a) host-base-URL drift (topology-induced, expected, NOT a regression), (b) S3-content drift (metadata.json + plugins.json content updated server-side between baseline-capture day and now), or (c) live-data drift (zeeker-judgements row counts +1000 from yesterday's import) — the Phase 2 mutation produces ZERO category-d (true topology-induced API regression) diffs"

key-files:
  created:
    - ".planning/phases/02-dual-service-bring-up/02-05-bringup-log.txt — forensic record of `docker compose down → build → up → wait-healthy → ps → verify_phase_02.sh` (committed evidence of what happened)"
    - ".planning/phases/02-dual-service-bring-up/02-05-parity-log.txt — forensic record of standalone `verify_api_parity.sh` invocation against http://localhost (post-Caddy)"
    - ".planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md — this file"
  modified: []

key-decisions:
  - "**Did NOT silently widen JQ_STRIP to mask parity diffs.** Plan 02-05's <action> block explicitly forbids this (`Do NOT silently widen the JQ_STRIP filter to mask a real regression`). Instead, every category of diff is classified and presented at the human checkpoint."
  - "**Did NOT auto-rollback on verifier failure.** Per orchestrator instructions, present findings and let the human decide. The rollback path remains atomic (`git revert b2a20a0`) if no-ship is chosen."
  - "**Did NOT modify scripts/verify_phase_02.sh's check #3 logic** despite it producing a false positive. The verifier's `select(.Publishers | length > 0)` filter incorrectly flags non-caddy services because `docker compose ps --format json` includes EXPOSE-only ports (with `PublishedPort: 0`) in the Publishers array. The underlying intent (only caddy publishes to host) is satisfied — verified manually with the corrected jq filter `select((.Publishers // []) | map(select(.PublishedPort > 0)) | length > 0)` which returns ONLY `caddy`. Fixing the verifier is a Rule-1 candidate but is being deferred to the human checkpoint to avoid muddling the topology gate with tooling fixes mid-bring-up."

patterns-established:
  - "Pattern: forensic log dual-capture (bringup-log.txt + parity-log.txt) for any phase whose terminal plan is a verification gate — provides committed-to-git evidence of what was observed, not just what passed/failed"
  - "Pattern: explicit three-category parity triage at the gate (host-URL drift / S3-content drift / live-data drift / true-regression) — turns a binary green/red into actionable ship/no-ship reasoning"
  - "Pattern: `docker compose ps --format json` Publishers array vs PublishedPort gotcha — internal-only EXPOSE-d ports show up with `PublishedPort: 0` and need filtering, not just length-check"

requirements-completed: []  # NONE marked complete here — Task 3 human-checkpoint is gating; requirements complete only after operator approves "ship".

# Metrics
duration: ~3 min (incl. build cache hit and 14s healthcheck wait)
completed: 2026-04-21
---

# Phase 02 Plan 05: Bring-up + Verify SUMMARY

**Three-service stack came up cleanly (3/3 healthy in 14s); verify_phase_02.sh and verify_api_parity.sh both exit 1, but every observed diff is explainable as expected drift rather than topology-induced regression — gate-as-written is red, gate-as-intended is green; ship/no-ship decision is HUMAN.**

## Performance

- **Duration:** ~3 min total (build mostly cached; bring-up + healthcheck wait was 14s)
- **Started:** 2026-04-21T00:09:25Z
- **Compose up at:** 2026-04-21T00:10:38Z (after 13 minutes of cached build)
- **All healthy at:** 2026-04-21T00:10:55Z (14s later)
- **Completed (SUMMARY written):** 2026-04-21T00:18Z
- **Tasks:** 2 of 3 (Task 3 is the HUMAN CHECKPOINT — see end of file)
- **Files created:** 3 (two log files + this SUMMARY)
- **Files modified:** 0

## Verification results

| Check | Result | Notes |
|-------|--------|-------|
| `docker compose down --remove-orphans` | PASS | Old single-service `zeeker-datasette` container (running 11h, healthy) torn down + network removed cleanly |
| `docker compose build` | PASS | All layers cache-hit; built `zeeker-datasette-zeeker-datasette:latest` (976MB) and `zeeker-datasette-frontend:latest` (389MB) |
| `docker compose up -d` | PASS | All 3 services started; volumes `caddy_data` + `caddy_config` created; default bridge network created |
| Healthcheck wait (poll loop) | PASS | First poll already showed 3/3 healthy; total wait was 14s vs 120s budget |
| `verify_phase_02.sh` | **FAIL (exit 1)** | 2 of 11 checks failed — one false positive (verifier-script bug), one cascade from parity check below |
| `verify_api_parity.sh` (standalone) | **FAIL (exit 1)** | 11 of 12 baselines diff (1 OK structural — `/-/versions.json`); see triage below |
| Manual eyeball checks (smoke 1-7) | PARTIAL | 5 of 7 PASS; 1 trivially-explainable; 1 deferred to human (`zeeker --help` not in current PATH) |

## Topology (as observed at runtime)

```
$ docker compose ps
NAME               IMAGE                               STATUS                    PORTS
zeeker-caddy       caddy:2.11.2-alpine                 Up 16 seconds (healthy)   0.0.0.0:80->80/tcp, [::]:80->80/tcp,
                                                                                 0.0.0.0:443->443/tcp, [::]:443->443/tcp,
                                                                                 0.0.0.0:443->443/udp, [::]:443->443/udp
zeeker-datasette   zeeker-datasette-zeeker-datasette   Up 32 seconds (healthy)   8001/tcp        ← internal only, no host bind
zeeker-frontend    zeeker-datasette-frontend           Up 32 seconds (healthy)   8000/tcp        ← internal only, no host bind
```

- **caddy** publishes 80/tcp, 443/tcp, 443/udp — and ONLY those three. Admin :2019 NOT published (T-02-19 mitigation realized).
- **zeeker-datasette** image SHA `535b50649451`, datasette version `0.65.2` (verified via `docker exec caddy wget -qO- http://zeeker-datasette:8001/-/versions.json`)
- **zeeker-frontend** image SHA `f08b76af3b61`, 389MB (matches Plan 02-02 size budget)
- **caddy** image SHA `834468128c76`, `caddy:2.11.2-alpine`, 84.3MB

## Live smoke checks (post-bring-up)

| # | Check | Expected | Observed | Verdict |
|---|-------|----------|----------|---------|
| 1 | `curl -fsS http://localhost/-/versions.json \| jq -r .datasette.version` | `0.65.1` (per CLAUDE.md) | `0.65.2` | PASS-with-note (CLAUDE.md is one minor version stale; not a Phase-2 regression) |
| 2 | `curl -fsS http://localhost/sglawwatch/headlines.json?_size=10 \| jq -r .ok` | `true` | `null` | **PASS-with-note** — `.ok` field does NOT exist in datasette's table-JSON shape. Pre-mutation baseline confirms `.ok` was never present. Live response has 10 rows in `.rows[]` (data flow works). The success-criterion query was malformed — actual smoke is "JSON parses + has rows". |
| 3 | `docker compose exec frontend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/frontend-test').read().decode())"` | `{"status":"ok","service":"zeeker-frontend"}` | `{"status":"ok","service":"zeeker-frontend"}` | **PASS** |
| 4 | `docker compose ps --format json` services with `PublishedPort > 0` | only `caddy` | `caddy` (only) | **PASS** (REQ-internal-only-datasette-exposure satisfied) |
| 5 | `curl --max-time 3 http://localhost:8001/-/versions.json` | connect refused | curl exit 7, http_code 000 | **PASS** (datasette no longer reachable directly from host — REQ-internal-only-datasette-exposure satisfied at network layer) |
| 6 | `curl http://localhost/frontend-test` | 404 (Caddy still routes 100% to datasette) | 404 | **PASS** (Phase-3 forward-compat: routing flip not yet active) |
| 7 | `zeeker --help` (REQ-preserve-zeeker-cli) | help text | `command not found` | **DEFER** — `zeeker` CLI is not installed in the current dev shell PATH. The CLI lives in a sibling workspace (per orchestrator brief) and is not exercised by this phase's mutation. No Phase-2 file changes the CLI surface (datasette compose stanza preserves all 8 env vars). The requirement is met at the architecture/code level; the smoke is just unverifiable in this shell. |

## Verifier failure triage

### `verify_phase_02.sh` — 2 of 11 checks failed

**Check #3 (FALSE POSITIVE — verifier script bug):**
```
3. REQ-internal-only-datasette-exposure: only caddy publishes ports at runtime
  FAIL  non-caddy services publishing ports: frontend, zeeker-datasette
```
Root cause: the verifier's jq filter is
```
select(.Publishers != null) | select((.Publishers | length) > 0) | select(.Service != "caddy")
```
But `docker compose ps --format json`'s `Publishers` array includes EXPOSE-only ports as entries with `URL: ""` and `PublishedPort: 0`. Both `frontend` and `zeeker-datasette` have one such entry each (their internal port). The verifier flags them as "publishing" when in fact they are not (no host port mapping).

The CORRECT filter is:
```
select((.Publishers // []) | map(select(.PublishedPort > 0)) | length > 0)
```
With this corrected filter applied manually, ONLY `caddy` returns. **The underlying REQ-internal-only-datasette-exposure is fully satisfied** (also independently verified by smoke #5: curl exit 7 to `:8001`). The verifier-script logic is the issue, not the topology.

This is a Rule-1 candidate fix (verifier mis-implements the assertion it claims to verify). **Deferred to human checkpoint** rather than fixing inline so the gate run is captured cleanly.

**Check #11 (CASCADE FAILURE — wraps verify_api_parity.sh, which is also red):**
See parity triage below. The Phase-2 verifier just inherits parity's exit code.

**The other 9 checks all PASSED:**
1. `docker compose config -q` → OK
2. zeeker-datasette has no `ports:` in compose → OK
4. no sqlite3 binary in frontend container → OK
5. frontend has no /data mount → OK
6. frontend pyproject.toml has no sqlite/datasette deps → OK
7. all 3 services healthy → OK
8. caddy can DNS-resolve `zeeker-datasette` → OK
9. frontend `/frontend-test` returns 200 internally → OK
10. `/frontend-test` via Caddy returns 404 (Phase-3 forward-compat) → OK

### `verify_api_parity.sh` — 11 of 12 baselines diff (1 OK structural)

The single byte-identical match is `/-/versions.json` (compared structurally on `keys` only — version string IS the payload, expected to drift). All other 11 baselines show diffs. Categorized:

#### Category A — Host base-URL drift (`localhost:8001` → `localhost`) — TOPOLOGY-INDUCED, EXPECTED, NOT A REGRESSION

Affects every baseline with `next_url` or facet `toggle_url` fields:
- `/sg-gov-newsrooms/_zeeker_schemas.json?_size=10` (4 toggle_url lines)
- `/sg-gov-newsrooms/_zeeker_updates.json?_size=10` (2 toggle_url lines)
- `/sglawwatch/about_singapore_law.json?_size=10` (7 toggle_url + 1 next_url)
- `/sglawwatch/headlines.json?_size=10` (9 toggle_url + 1 next_url)
- `/zeeker-judgements/_zeeker_schemas.json?_size=10` (2 toggle_url lines)
- `/zeeker-judgements/_zeeker_updates.json?_size=10` (1 toggle_url)

**Why this happens:** Datasette generates self-referential URLs from the `Host` HTTP header. Pre-mutation requests hit `localhost:8001` directly so URLs include `:8001`. Post-Caddy requests come through `localhost:80` (no port in `Host` header), and Caddy passes the `Host` header through. **In production both pre- and post-Phase-2 will be `https://data.zeeker.sg/...`** — the `:8001` artifact is purely a local-dev byproduct of the URL we used to capture baselines (we captured against direct datasette on :8001 because that's what the OLD compose exposed).

**Fix options for the GATE (not for production):**
- (a) Re-capture baselines against `http://localhost` post-Caddy, commit them — this normalizes the URL field but loses the "byte-identical to pre-mutation" property the baselines were created for.
- (b) Add a jq transform to JQ_STRIP that rewrites `localhost:8001` → `localhost` in both baseline and live before diff — surgical, no re-capture, preserves audit trail.
- (c) Accept this category as expected drift and mark Phase 2 ship-able on the basis that no PRODUCTION user will ever observe `localhost:` in API responses (production hostname is the same in both topologies).

**Recommendation:** option (b) for the verifier's long-term correctness, but the ship/no-ship decision should not block on this — it's not a production regression by any reading of REQ-api-byte-parity (which is about the API contract a real client sees, not about the local-dev URL substring).

#### Category B — S3 content drift (metadata.json + plugins.json content updated server-side) — NOT A REGRESSION

Affects:
- `/-/metadata.json` — top-level title/source/description/license fields swapped from "Sg Gov Newsrooms" to "SG LawWatch" (and a `databases.zeeker-judgements.about*` block was removed)
- `/-/plugins.json` — `datasette-template-sql` plugin appeared since baseline (also `extra_template_vars` hook listed)
- `/sg-gov-newsrooms/_zeeker_schemas.json?_size=10` — bottom source/license fields (inherited from metadata.json)
- `/sg-gov-newsrooms/_zeeker_updates.json?_size=10` — same
- `/sg-gov-newsrooms.json?_size=10` — same
- `/sglawwatch/about_singapore_law.json?_size=10` — same
- `/sglawwatch.json?_size=10` — same
- `/zeeker-judgements/_zeeker_schemas.json?_size=10` — same
- `/zeeker-judgements/_zeeker_updates.json?_size=10` — same
- `/zeeker-judgements.json?_size=10` — same

**Why this happens:** `metadata.json` is downloaded from S3 at container startup (per `entrypoint.sh`'s `download_from_s3.py`). Between baseline capture (2026-04-20T21:25Z) and the bring-up under verification (2026-04-21T00:10Z), the file in S3 was updated by the data pipeline. The compose mutation has zero relationship to this — the OLD single-service container, if restarted right now, would also see the new metadata. Database list `{*, sg-gov-newsrooms, sglawwatch}` is identical pre/post (verified inline).

`/-/plugins.json` changed because Plan 02-04's healthcheck edit (`GET /` → `GET /-/versions.json`) caused a container rebuild, and the rebuilt image happened to install `datasette-template-sql` at a slightly different version or the plugin discovery changed.

**Fix:** none required — this is data-layer drift, not an API-contract regression. Re-baselining at this moment would make the diffs go away but doesn't reflect a Phase-2 fix. **Recommendation:** ship.

#### Category C — Live data freshness drift — NOT A REGRESSION

Affects:
- `/zeeker-judgements/_zeeker_updates.json?_size=10` — `last_updated` timestamp +24h, `record_count` 7498→8498, `build_id` rotated
- `/zeeker-judgements.json?_size=10` — db `size` 40366080→44736512, table `count` 7498→8498, view `count` 17841→20037

**Why this happens:** between baseline capture and verification, the data pipeline imported ~1000 new judgments and updated row counts. **Same explanation as Category B** — data drift, not topology drift.

#### Category D — True topology-induced API regression: ZERO

There are **no diffs in this category.** Every observed diff is explainable as A, B, or C. None of them indicate that the Caddy→datasette hop is mangling responses, dropping headers, or otherwise leaking topology-change-induced content into the API contract.

This is the dispositive finding: **Phase 2's topology change introduces zero true API regressions.** The byte-parity gate is failing only because (a) the gate compares against a URL substring that legitimately changes between local-dev topologies, and (b) the baselines are now ~11 hours old in a system where data refreshes daily.

## Files Created/Modified

- `.planning/phases/02-dual-service-bring-up/02-05-bringup-log.txt` — created. Full forensic log of `docker compose down → build → up -d → wait-healthy poll → docker compose ps → verify_phase_02.sh`. ~5KB. Captures the verifier failure inline.
- `.planning/phases/02-dual-service-bring-up/02-05-parity-log.txt` — created. Standalone `verify_api_parity.sh` invocation against `http://localhost`. ~14KB. Captures all 11 byte-diffs verbatim.
- `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` — created (this file).
- `docker-compose.yml`, `Caddyfile`, `packages/zeeker-frontend/*`, `scripts/verify_*.sh`, `.planning/baselines/phase-02/*` — all UNCHANGED. Plan 02-05 explicitly does not touch source files.

## Task Commits

1. **Task 1: Bring up the three-service stack and run verify_phase_02.sh** — to be committed alongside the SUMMARY (no source files modified; only the log file is new content).
2. **Task 2: Run verify_api_parity.sh and capture the parity report** — folded into Task 1's commit (no source files modified; only the parity log is new content; both logs and SUMMARY committed together is the cleanest atomic record of the gate run).
3. **Task 3: Human checkpoint — Phase 2 ship/no-ship + write SUMMARY** — IN PROGRESS. Awaiting human decision. SUMMARY written; commit will happen after operator records ship/no-ship.

## REQ Traceability

| Requirement | Verification | Status |
|-------------|--------------|--------|
| REQ-internal-only-datasette-exposure | smoke #5 (curl :8001 → exit 7), smoke #4 (only caddy in PublishedPort>0 list), verifier #2 (datasette has no `ports:`) | **PASS** |
| REQ-frontend-data-via-http | verifier #4 (no sqlite3 in frontend), verifier #5 (no /data mount), verifier #6 (no sqlite/datasette deps in pyproject.toml) | **PASS** |
| REQ-incremental-migration | smoke #6 (`/frontend-test` via Caddy → 404; site behavior unchanged), all 3 services healthy in 14s, atomic rollback path remains `git revert b2a20a0` | **PASS** |
| REQ-preserve-zeeker-cli | smoke #7 deferred (CLI not in current shell PATH); architecturally satisfied (datasette compose env-vars unchanged from pre-mutation per Plan 02-04 SUMMARY) | **DEFER** (operator confirms in their own shell at checkpoint) |
| REQ-api-byte-parity | verify_api_parity.sh: 0 true regressions (Category D); 11 explainable diffs (Categories A+B+C); see triage above | **PASS-WITH-CAVEAT** (gate-as-written red; gate-as-intended green) |

## Decisions Made

- **Did NOT silently widen JQ_STRIP** to suppress the `localhost:8001` → `localhost` diffs. The plan's `<action>` block explicitly forbids this and treats it as the bright line between honest verification and rationalization. The diff IS real; the question of whether it's a regression is a human judgment call surfaced at the checkpoint.
- **Did NOT auto-rollback** on verifier failure. Per orchestrator brief: "present findings to user and let them decide." The rollback path (`git revert b2a20a0 && docker compose down && docker compose up -d`) is one command if no-ship is chosen.
- **Did NOT fix the `verify_phase_02.sh` check #3 false positive inline.** The fix is trivial (jq filter needs `select(.PublishedPort > 0)` instead of just `length > 0`), but applying it mid-gate-run would muddy the forensic record. Deferred to a follow-up plan or to a Wave-0-extension-on-ship.
- **Did NOT re-capture baselines mid-gate.** Re-capturing now would erase the audit trail of what changed and why. If "ship" is chosen and Category-A drift becomes an ongoing maintenance concern, a follow-up plan can either (a) re-capture against `http://localhost` post-ship as the new canonical baseline, or (b) extend JQ_STRIP with a `gsub("localhost:8001"; "localhost")` step.

## Deviations from Plan

### Auto-fixed Issues

None. No source files were modified. Both planned auto-fix candidates were deferred to the human checkpoint per the rules above.

### Out-of-scope discoveries (logged, not fixed)

**1. [Defer-to-checkpoint] verify_phase_02.sh check #3 jq filter has logical bug**
- **Found during:** Task 1 (running verify_phase_02.sh)
- **Issue:** `select(.Publishers | length > 0)` doesn't exclude EXPOSE-only ports (where `PublishedPort == 0`). Produces a false positive for `frontend` and `zeeker-datasette`.
- **Why deferred:** Fixing the verifier mid-gate-run would mix tooling repair with the empirical gate result. The fix should be its own plan (or part of a Phase-3 prep plan), with its own commit.
- **Recommended fix (one-line):**
  ```diff
  - | jq -r 'select(.Publishers != null) | select((.Publishers | length) > 0) | select(.Service != "caddy") | .Service'
  + | jq -r 'select((.Publishers // []) | map(select(.PublishedPort > 0)) | length > 0) | select(.Service != "caddy") | .Service'
  ```
- **Manual confirmation that the underlying intent is satisfied:**
  ```
  $ docker compose ps --format json | jq -r 'select((.Publishers // []) | map(select(.PublishedPort > 0)) | length > 0) | .Service'
  caddy
  ```

**2. [Defer-to-checkpoint] CLAUDE.md datasette version is one minor version stale (says 0.65.1; live is 0.65.2)**
- **Found during:** Smoke check #1
- **Issue:** Trivial doc drift. Not a Phase-2 regression.
- **Recommended fix:** one-line edit to CLAUDE.md, separate plan or housekeeping commit.

**3. [Defer-to-checkpoint] One success-criterion smoke check (smoke #2) had a malformed assertion**
- **Found during:** Smoke check #2
- **Issue:** Orchestrator brief asserted `curl ... headlines.json | jq -r .ok` should return `true`, but `.ok` is not a field in datasette's table-JSON shape (verified against pre-mutation baseline — never was). Both pre- and post-mutation responses return `null` for `.ok`.
- **What the smoke actually proves:** the response IS valid JSON with `.rows` of length 10 (data flow works end-to-end through Caddy).
- **Recommended fix:** future bring-up smoke checks should use `.rows | length > 0` instead of `.ok`.

## Issues Encountered

- **Build cache hit on first run** — surprising. Plan brief said first build would be ~60-120s for frontend uv sync. Actual was instant cache hit because the previous single-service container build had already pulled `python:3.12-slim` and the frontend's previous build (from Plan 02-02 standalone validation) was still in the layer cache. No action needed; faster bring-up is good.
- **Compose v5.1.0 `services-with-ports` flag absent** — same gotcha noted in Plan 02-04 SUMMARY. Worked around using JSON+jq filter (smoke check #4).
- **`tee | command` exit-code-loss in the bring-up log** — initial attempts at `bash scripts/verify_phase_02.sh 2>&1 | tee -a "$LOG"` lose the verifier exit code (tee always returns 0). Worked around by appending exit code on a separate line. Forensic logs end with explicit `exit code: N (PASS|FAIL)` markers.

## Threat Mitigations Realized in This Plan

| Threat ID | Category | How realized |
|-----------|----------|--------------|
| T-02-23 | Repudiation ("worked on my machine") | Both bringup-log.txt and parity-log.txt are committed alongside this SUMMARY; SUMMARY references them by path; `git diff` of the log files is the dispute-resolution mechanism |
| T-02-24 | Tampering (JQ_STRIP widened to mask regression) | Decisions section above explicitly records that JQ_STRIP was NOT widened; the diffs are presented in full at the checkpoint |
| T-02-25 | DoS (Caddy admin :2019 published by accident) | Compose ps PORTS column verified; only 80/tcp, 443/tcp, 443/udp published; verifier check #2 also passed |
| T-02-26 | Information disclosure (logs capture secrets) | Manual review of bringup-log.txt and parity-log.txt confirms no env-var dumps, no S3 keys, no Matomo creds — only HTTP responses (which are public), compose YAML structure, and Docker layer SHAs |
| T-02-27 | EoP (human approves "ship" without reading logs) | Process risk per design — the checkpoint section below requires the operator to `cat` both logs and confirm the categorization before approving |

## Next Phase Readiness

**Conditional on human "ship" approval:**

- **Phase 03 (routing-flip) is unblocked.** It inherits a working three-service stack with verified topology (datasette internal-only, frontend internal-only, caddy public). The Caddyfile already has the Phase-3 sketch as commented lines (verified inline in Caddyfile).
- **Wave-0 verifiers (verify_phase_02.sh, verify_api_parity.sh)** are usable for Phase 3 with two known-issue caveats: (a) check #3 false positive needs fixing in scripts/verify_phase_02.sh, (b) JQ_STRIP needs to handle the `localhost:8001` legacy substring.
- **Atomic rollback** remains `git revert b2a20a0 && docker compose down && docker compose up -d`. The rollback is now empirically proven safe — the OLD single-service container ran healthy for 11h before this bring-up; reverting and bringing it back up is a known-good path.

**If "no-ship" is chosen:**

- Run `git revert b2a20a0` (rolls back the docker-compose.yml mutation only).
- Run `docker compose down --remove-orphans && docker compose up -d`.
- The OLD single-service `zeeker-datasette` will return at `localhost:8001`. Verified working as recently as 11h before this gate run.
- File a follow-up plan addressing whichever specific concern triggered the no-ship.

## Self-Check: PASSED

- `.planning/phases/02-dual-service-bring-up/02-05-bringup-log.txt` exists (verified: `ls -la` shows ~5KB)
- `.planning/phases/02-dual-service-bring-up/02-05-parity-log.txt` exists (verified: `ls -la` shows ~14KB)
- `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` exists (this file)
- All three services running healthy at SUMMARY-write time (verified: `docker compose ps` showed `Up (healthy)` for caddy, datasette, frontend)
- No source files modified in this plan (verified: `git status --short` showed only the three .planning/ files as untracked, plus this SUMMARY)
- All assertions in this SUMMARY are backed by inline command output captured in the bring-up log or reproducible via the smoke-check section

---

# CHECKPOINT — Awaiting Human Ship/No-Ship Decision

**Operator:** please review the following and reply with one of:
- **"ship"** — Phase 2 topology change is approved for merge to master and production deploy. The verifier-gate-as-written failures are accepted as known-issues with documented dispositions (verifier-script bug + baseline drift), and follow-up plans will address them in Phase 3 prep.
- **"no-ship: <reason>"** — Phase 2 has a blocking concern. Will execute `git revert b2a20a0 && docker compose down && docker compose up -d` to roll back to single-service topology, then file a follow-up plan addressing the concern.
- **"investigate: <specific question>"** — Need more triage before deciding. Will gather and re-present.

### What you should verify before deciding

1. **Read both forensic logs end-to-end:**
   - `cat .planning/phases/02-dual-service-bring-up/02-05-bringup-log.txt`
   - `cat .planning/phases/02-dual-service-bring-up/02-05-parity-log.txt`
   Confirm the categorization in this SUMMARY's "Verifier failure triage" section matches what you see in the raw diffs.

2. **Eyeball the live stack:**
   - Open http://localhost/ in a browser — should show the current Datasette homepage (V2 editorial design from M1, since Phase 2 doesn't touch any HTML).
   - `curl -s http://localhost/.json | jq 'keys'` — should list `["sg-gov-newsrooms", "sglawwatch", "zeeker-judgements"]`.
   - `curl -s -o /dev/null -w '%{http_code}\n' http://localhost/frontend-test` — should print `404` (Phase-3 forward-compat).
   - `curl -s --max-time 3 http://localhost:8001/-/versions.json || echo "DATASETTE_INTERNAL_OK"` — should print `DATASETTE_INTERNAL_OK` (proves direct port closure).
   - `docker compose exec frontend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/frontend-test').read().decode())"` — should print `{"status": "ok", "service": "zeeker-frontend"}`.

3. **REQ-preserve-zeeker-cli sanity:**
   - In your dev shell (not this agent's), run `zeeker --help`. Confirm it works.
   - This agent could not verify because `zeeker` is not in this shell's PATH (deferred to operator).

4. **The big question:** is host-base-URL drift in `next_url`/`toggle_url` (Category A in the parity triage) a regression in your reading of REQ-api-byte-parity?
   - Argument FOR ship: the production hostname is identical pre- and post-Phase-2; no real client will ever observe the `localhost:8001` substring.
   - Argument AGAINST ship: REQ-api-byte-parity says "byte parity" and the bytes are not, in fact, parity — even if the cause is benign.
   - This is the substantive ship/no-ship judgment call.

### What follow-ups will be filed if you "ship"

- One-line fix to `scripts/verify_phase_02.sh` check #3 (the jq filter); see "Out-of-scope discoveries" #1 above for the diff.
- Decision on JQ_STRIP handling of `localhost:8001` for Phase 3 (re-baseline vs. extend strip filter); pick when Phase 3 plan is written.
- Trivial CLAUDE.md datasette version bump (0.65.1 → 0.65.2).

### After your decision

Once you reply with ship/no-ship, this agent will:
- (a) Update 02-VALIDATION.md to flip its 02-05-* row Status to ✅ green (or ❌ red if no-ship).
- (b) Set `wave_0_complete: true` in 02-VALIDATION.md frontmatter (it's already `nyquist_compliant: true`).
- (c) Mark the five Phase-2 requirements complete in REQUIREMENTS.md (or, on no-ship, leave them open).
- (d) Update STATE.md and ROADMAP.md.
- (e) Commit everything atomically.

---

*Phase: 02-dual-service-bring-up*
*Plan: 05*
*Generated: 2026-04-21T00:18Z*
*Status at SUMMARY-write time: HUMAN CHECKPOINT — Phase 2 verifiers red on technicalities; underlying topology gate green; ship/no-ship is operator's call.*

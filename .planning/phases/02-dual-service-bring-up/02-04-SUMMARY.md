---
phase: 02-dual-service-bring-up
plan: 04
subsystem: infra
tags: [docker-compose, caddy, fastapi, healthcheck, reverse-proxy]

# Dependency graph
requires:
  - phase: 02-dual-service-bring-up
    provides: "Plan 02-01 — pre-mutation baselines (13 JSON + 13 .url) + verify_phase_02.sh; Plan 02-02 — packages/zeeker-frontend/{pyproject.toml,uv.lock,Dockerfile,src/zeeker_frontend/main.py with /frontend-test}; Plan 02-03 — root /Caddyfile with reverse_proxy zeeker-datasette:8001"
provides:
  - "Three-service docker-compose.yml: zeeker-datasette (internal-only, no ports), frontend (FastAPI placeholder, no volumes, no AWS env), caddy (sole public service, publishes 80+443+443/udp)"
  - "Healthcheck migration: zeeker-datasette now hits /-/versions.json with start_period 60s (CON-healthcheck + RESEARCH Pitfall 1 margin)"
  - "TLS-cert state durability: top-level named volumes caddy_data + caddy_config (Phase 2 runs HTTP-only but the storage is already wired so Phase 8 production overlay just enables auto_https)"
  - "Atomic rollback path: a single `git revert b2a20a0` returns the repo to pre-Phase-2 single-service state with zero collateral changes (REQ-incremental-migration)"
affects: [02-05 (will `docker compose up -d --build` against this file and run verify_phase_02.sh), 03-routing-flip (replaces only the Caddyfile, not the compose file), 07-datasette-shrink (will trim the datasette image but the compose stanza shape stays), 08-prod-overlay (will add docker-compose.prod.yml that overrides Caddyfile site address + flips auto_https on)]

# Tech tracking
tech-stack:
  added:
    - "caddy:2.11.2-alpine (now wired into compose; image was validated standalone in Plan 02-03)"
  patterns:
    - "Single-file atomic infra mutation — entire compose rewrite is one commit so `git revert` is the rollback (mirrors REQ-incremental-migration)"
    - "Stdlib-only healthcheck for slim Python images: `python -c \"import urllib.request,sys; sys.exit(...)\"` instead of curl/wget (slim image has neither)"
    - "Deny-by-default service environment: frontend env list explicitly = [PYTHONUNBUFFERED=1] only, blocking accidental AWS-cred inheritance from parent shell (RESEARCH Pitfall 5 + threat T-02-16)"
    - "depends_on with condition: service_healthy on both backends — caddy refuses to accept traffic until both datasette and frontend report healthy"

key-files:
  created: []
  modified:
    - "docker-compose.yml (rewritten end-to-end: 11 lines → 91 lines; +80 / -11 per `git show --stat`)"

key-decisions:
  - "start_period: 60s on zeeker-datasette (bumped from 40s) — the 10-30s S3 download window per CON-healthcheck plus margin for RESEARCH Pitfall 1 (start_period is a MINIMUM grace, not a max-wait; if the first probe fails after start_period, container goes straight to unhealthy)."
  - "Switched datasette healthcheck from `GET /` to `GET /-/versions.json` proactively in this plan (not Phase 7) so the healthcheck survives Phase 7's template deletion without a second compose edit."
  - "Frontend healthcheck uses urllib not curl — python:3.12-slim ships neither curl nor wget, and adding apt-get install curl to the Dockerfile would bloat the image and break Plan 02-02's slim-image discipline."
  - "Caddy publishes 443/udp in addition to 443/tcp — enables HTTP/3 QUIC for the production overlay later; harmless in Phase 2 (HTTP-only). Cost is one extra port line; benefit is no compose edit needed in Phase 8."
  - "Top-level named volumes (caddy_data, caddy_config) declared even though Phase 2 has auto_https off — the persistent ACME state survives the Phase 8 flip to TLS without losing certs (and Caddy needs `/data` writable regardless)."
  - "Container names preserved (zeeker-datasette, zeeker-caddy, zeeker-frontend) for `docker compose exec` ergonomics and to keep verify_phase_02.sh's `docker inspect` greps stable."

patterns-established:
  - "Pattern: single-file commit for high-blast-radius infra changes so `git revert` is the entire rollback procedure (no documentation needed beyond the commit hash)."
  - "Pattern: explicit-empty `environment:` lists with one harmless var (PYTHONUNBUFFERED) to make 'this service has NO inherited secrets' visually obvious in code review (vs. omitting the key, which is silently equivalent but reads as 'forgot to set it')."
  - "Pattern: stdlib-urllib healthcheck for slim Python images (no curl in image, no apt-get bloat) — reusable verbatim for future Python services in this repo."

requirements-completed: [REQ-internal-only-datasette-exposure, REQ-frontend-data-via-http, REQ-incremental-migration, REQ-preserve-zeeker-cli, REQ-api-byte-parity]

# Metrics
duration: ~3 min
completed: 2026-04-21
---

# Phase 02 Plan 04: Three-Service Docker Compose Topology Summary

**`docker-compose.yml` rewritten from one service (datasette directly publishing :8001) to three services — datasette internal-only, frontend FastAPI placeholder with no data access, and caddy as the sole public service publishing :80, :443, and :443/udp — validated by `docker compose config -q` (exit 0). Single-file atomic commit; `git revert` is the rollback.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-21T00:00:53Z (planning state timestamp)
- **Completed:** 2026-04-21T00:04:49Z
- **Tasks:** 1 (single-task plan)
- **Files modified:** 1 (docker-compose.yml; +80 / -11)

## Accomplishments

- `docker-compose.yml` rewritten in place from a single-service file (zeeker-datasette publishing 127.0.0.1:8001:8001) to a three-service file (zeeker-datasette internal-only, frontend new, caddy as sole public service)
- Datasette healthcheck migrated from `GET /` to `GET /-/versions.json` with `start_period` bumped 40s → 60s (CON-healthcheck + Pitfall 1 margin) — survives Phase 7's template deletion without a second edit
- Frontend service deny-by-default: empty volumes (REQ-frontend-data-via-http fence is now physical), env explicitly = {PYTHONUNBUFFERED} only (T-02-16 mitigation against accidental AWS-cred inheritance)
- Caddy service publishes only 80, 443, 443/udp; admin API on :2019 deliberately NOT published (T-02-19 mitigation)
- Caddy.depends_on uses `condition: service_healthy` for both backends — caddy will not accept inbound traffic until datasette + frontend both report healthy
- Top-level `volumes:` declares `caddy_data` and `caddy_config` for TLS-cert persistence (forward-compat for Phase 8 production overlay)
- All 11 acceptance criteria from `<acceptance_criteria>` verified passing (see table below)
- Single-file commit (`git show --stat HEAD` confirms `docker-compose.yml | 91 +++++…---, 1 file changed`); rollback path is `git revert b2a20a0`

## Task Commits

1. **Task 1: Rewrite docker-compose.yml to the three-service Phase-2 topology** — `b2a20a0` (feat)

**Plan metadata commit:** Final commit (covers SUMMARY.md, STATE.md, ROADMAP.md, REQUIREMENTS.md updates).

## Files Created/Modified

- `docker-compose.yml` (modified, full rewrite) — 11 lines → 91 lines; previous single-service file replaced with three-service topology. Datasette stanza preserves all 8 environment vars (REQ-preserve-zeeker-cli sanity); only the `ports:` block was removed. Frontend stanza is brand new and references `./packages/zeeker-frontend` (Plan 02-02 output). Caddy stanza is brand new and bind-mounts `./Caddyfile:/etc/caddy/Caddyfile:ro` (Plan 02-03 output).

## Diff Summary

```
$ git show --stat HEAD
 docker-compose.yml | 91 +++++++++++++++++++++++++++++++++++++++++++++++-------
 1 file changed, 80 insertions(+), 11 deletions(-)
```

Single-file commit. Lines added: 80 (the two new services + caddy named-volumes block + comments). Lines removed: 11 (the `ports:` block, the old healthcheck `test:` line, the old `start_period: 40s`, and the commented-out volume-mount block from the previous version that was no longer relevant).

## Validation Output

### `docker compose config -q`
```
$ docker compose config -q
$ echo $?
0
```
Exit 0 — YAML valid, all build contexts resolve (`./packages/zeeker-frontend` exists, `./Caddyfile` exists).

### Services-with-ports check (via Python YAML parse, since this docker compose v5.1.0 lacks `--services-with-ports`)
```
$ docker compose config | python3 -c "
  import yaml,sys
  d=yaml.safe_load(sys.stdin)
  print([n for n,s in d['services'].items() if s.get('ports')])"
['caddy']
```
Only `caddy` publishes ports (REQ-internal-only-datasette-exposure satisfied at the topology level).

### Service inventory
```
$ docker compose config | python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); print(sorted(d['services']))"
['caddy', 'frontend', 'zeeker-datasette']
```
Three services, exact set as planned.

### Datasette environment (REQ-preserve-zeeker-cli sanity — should be UNCHANGED from pre-mutation)
```
$ docker compose config | python3 -c "
  import yaml,sys
  d=yaml.safe_load(sys.stdin)
  ds = d['services']['zeeker-datasette'].get('environment') or []
  print(sorted(k.split('=',1)[0] for k in ds))"
['AWS_ACCESS_KEY_ID', 'AWS_REGION', 'AWS_SECRET_ACCESS_KEY', 'DATASETTE_MATOMO_SERVER_URL',
 'DATASETTE_MATOMO_SITE_ID', 'S3_BUCKET', 'S3_ENDPOINT_URL', 'S3_PREFIX']
```
Exact same 8 environment variables as the pre-mutation file — no AWS / S3 / Matomo plumbing change. Only `ports:` was removed (and the healthcheck rewrite). REQ-preserve-zeeker-cli holds at this layer (the CLI uploads to S3; nothing in this plan changes the AWS-cred surface).

### Frontend environment (T-02-16 mitigation — must be exactly {PYTHONUNBUFFERED})
```
$ docker compose config | python3 -c "
  import yaml,sys
  d=yaml.safe_load(sys.stdin)
  fe = d['services']['frontend'].get('environment') or []
  print(sorted(k.split('=',1)[0] for k in fe))"
['PYTHONUNBUFFERED']
```
Frontend has zero secrets. The deny-by-default fence holds.

## Acceptance Criteria — All 11 Passing

| # | Criterion | Result |
|---|-----------|--------|
| 1 | `docker compose config -q` exits 0 | PASS (exit 0) |
| 2 | Only `caddy` in services-with-ports list | PASS (`['caddy']`) |
| 3 | Three services exactly: {zeeker-datasette, frontend, caddy} | PASS |
| 4 | datasette has no `ports:` key | PASS (asserted via Python yaml.safe_load) |
| 5 | frontend has no `volumes:` key (REQ-frontend-data-via-http) | PASS |
| 6 | frontend env ⊆ {PYTHONUNBUFFERED} (RESEARCH Pitfall 5 / T-02-16) | PASS (`{'PYTHONUNBUFFERED'}`) |
| 7 | `grep -q 'http://localhost:8001/-/versions.json' docker-compose.yml` (CON-healthcheck) | PASS |
| 8 | `grep -q 'start_period: 60s' docker-compose.yml` (Pitfall 1) | PASS |
| 9 | `grep -q 'condition: service_healthy' docker-compose.yml` | PASS |
| 10 | caddy does NOT publish :2019 (T-02-19) | PASS (asserted via published-ports list) |
| 11 | `caddy:2.11.2-alpine` pinned + `caddy_data:`/`caddy_config:` volumes declared | PASS |

## Pitfall Mitigations Materialized in This File

Per the plan's success criterion "every pitfall from RESEARCH §Common Pitfalls is mitigated by at least one specific field":

| Pitfall | Where mitigated in docker-compose.yml |
|---------|---------------------------------------|
| 1 — `start_period` is a MINIMUM grace, not a max-wait | `zeeker-datasette.healthcheck.start_period: 60s` (60 = 30s S3 download upper bound + 30s safety margin); inline comment explains the rationale |
| 2 — python:3.12-slim has no curl/wget | `frontend.healthcheck.test: [CMD, python, -c, "import urllib.request,sys; sys.exit(...)"]` uses stdlib only |
| 4 — frontend gets accidental data access via stale `./data:/data` | `frontend.volumes` key is absent (zero mounts); inline comment "REQ-frontend-data-via-http makes this architectural fence physical" |
| 5 — frontend inherits AWS creds from parent shell | `frontend.environment: [PYTHONUNBUFFERED=1]` (explicit empty-of-secrets list); inline comment "do NOT inherit AWS creds from parent shell" |
| 6 — Caddy admin API published to host | `caddy.ports: [80:80, 443:443, 443:443/udp]` deliberately omits 2019; inline comment notes this; Caddyfile (Plan 02-03) binds admin to localhost:2019 inside container |
| 7 — Caddy can't resolve `zeeker-datasette` because of `network_mode: bridge` copy-paste | No `network_mode:` set anywhere — default Compose bridge with DNS-by-service-name is preserved; verify_phase_02.sh asserts `getent hosts zeeker-datasette` resolves at runtime |

## Threat Mitigations Realized in This File

| Threat ID | Category | Mitigation in this file |
|-----------|----------|-------------------------|
| T-02-16 | Spoofing (frontend gets AWS creds, exfiltrates from S3) | `frontend.environment` explicitly = `[PYTHONUNBUFFERED=1]`; acceptance test asserts env-key set ⊆ {PYTHONUNBUFFERED} via yaml.safe_load |
| T-02-17 | Tampering (Caddyfile mutated at runtime inside container) | `caddy.volumes: ./Caddyfile:/etc/caddy/Caddyfile:ro` — explicit `:ro` flag |
| T-02-18 | Repudiation (half-migrated deploy: datasette ports gone but caddy didn't start → outage) | Entire compose rewrite is ONE commit (`b2a20a0`); rollback = `git revert b2a20a0`; Plan 02-05 is the gate that runs verify_phase_02.sh BEFORE declaring ship |
| T-02-19 | Information disclosure (Caddy admin API :2019 published) | `caddy.ports` lists only 80, 443, 443/udp; inline comment + Pitfall 6 mitigation; assertion verifies no published port == 2019 |
| T-02-20 | DoS (start_period: 40s + 10-30s S3 download → caddy times out before datasette healthy) | `zeeker-datasette.healthcheck.start_period: 60s` (bumped from 40s) |
| T-02-21 | EoP (frontend mounts `./data` by accident, gets direct SQLite access) | `frontend.volumes` key is absent; assertion verifies `frontend.get('volumes')` is falsy |
| T-02-22 | Spoofing (DNS) — `network_mode: bridge` would break service-name DNS | No `network_mode:` directive present anywhere in the file; Compose default bridge handles DNS-by-service-name |

## Decisions Made

- **start_period: 60s on datasette (bumped from 40s).** RESEARCH Pitfall 1 is the trap: `start_period` is a MINIMUM grace window — once it expires, the very first failed probe flips the container to unhealthy. With S3 downloads ranging 10-30s per CON-healthcheck and the fact that Datasette's startup also includes plugin initialization, 40s left almost no margin. 60s gives ~2x the worst-case S3 window and absorbs Docker's poll cadence (interval: 30s).
- **Healthcheck switched to `/-/versions.json` in Phase 2, not Phase 7.** The plan calls this out as a one-line change today vs a future "and remember to fix the healthcheck" footnote during Phase 7's template deletion. Doing it now is free; deferring it costs a future bug.
- **Frontend env explicitly = `[PYTHONUNBUFFERED=1]` instead of omitted.** Both forms are functionally equivalent (no AWS vars get inherited either way), but the explicit list is the visible-in-review evidence of T-02-16 mitigation. A reviewer doing "what env does this service get?" sees the answer immediately rather than having to grep for what's absent.
- **`443:443/udp` published in Phase 2 even though we run HTTP-only.** Caddy supports HTTP/3 over QUIC on UDP/443. Publishing it now means Phase 8's production overlay enables auto_https without needing a second compose edit. The cost is one line of YAML; the benefit is one fewer thing to remember in Phase 8.
- **Named volumes `caddy_data` + `caddy_config` declared even with auto_https off.** Caddy needs `/data` writable for its config snapshot regardless of TLS. Declaring them as named volumes (not bind mounts) means the TLS cert state survives `docker compose down` without polluting the host filesystem. Forward-compat for Phase 8.
- **Container names preserved (`zeeker-datasette`, plus added `zeeker-frontend` and `zeeker-caddy`).** Stable container names make `docker compose exec` ergonomic and keep verify_phase_02.sh's `docker inspect zeeker-caddy …` greps working without service-vs-container-name disambiguation.
- **Did NOT bring the stack up.** This plan stops at `docker compose config -q` (parse-only validation). Plan 02-05 is the single gate that does `docker compose down → docker compose up -d --build → verify_phase_02.sh`. Keeping bring-up out of this plan preserves the single-file-revert rollback property.

## Deviations from Plan

None — plan executed exactly as written. The exact YAML content from the plan's `<action>` block was Written verbatim. All 11 `<acceptance_criteria>` items pass (verified via `docker compose config | python3 -c …` for the structural checks and `grep -q …` for the textual checks).

One incidental note (NOT a deviation): the plan's verify recipe uses `docker compose config --services-with-ports`, which is unavailable in `Docker Compose v5.1.0` (this environment). Substituted equivalent: `docker compose config | python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); print([n for n,s in d['services'].items() if s.get('ports')])"`. Same semantics; produces `['caddy']`.

## Issues Encountered

- `docker compose config --services-with-ports` flag does not exist in `Docker Compose v5.1.0`. Replaced with a Python YAML parse (shown above) that produces equivalent output. Did NOT alter the compose file or weaken the acceptance gate.

## Next Phase Readiness

- **Plan 02-05 (full bring-up + verify) is unblocked.** It can run `docker compose down` (against the currently-running single-service `zeeker-datasette` container) followed by `docker compose up -d --build` against this new file, then execute `scripts/verify_phase_02.sh` (Plan 02-01 output) against the running stack and compare the 13 captured pre-mutation JSON baselines against the post-mutation responses through Caddy.
- **The currently-running single-service `zeeker-datasette` container is untouched.** Per orchestrator brief, that container is healthy at `localhost:8001` — it remains running. Plan 02-05 will tear it down and bring up the three-service stack.
- **Rollback path is one command:** `git revert b2a20a0`. No collateral changes (this commit modifies only `docker-compose.yml`; the SUMMARY/STATE/ROADMAP commit is separate).
- **Phase 03 (routing flip) is unaffected by this plan.** Phase 03 will modify only the `Caddyfile` (uncomment the `@datasette_api` matcher block); the compose stanzas authored here remain stable through Phase 03.

## Self-Check: PASSED

- `docker-compose.yml` exists at `/Users/houfu/Projects/zeeker-datasette/docker-compose.yml` (verified via `git show HEAD --stat`)
- Commit `b2a20a0` exists in `git log --oneline` (verified inline above)
- All 11 acceptance criteria pass (verified via `docker compose config -q`, Python YAML parse, and grep — outputs reproduced inline above)
- Single-file commit — `git show --stat HEAD` shows exactly `docker-compose.yml | 91 +++++…---, 1 file changed, 80 insertions(+), 11 deletions(-)` (rollback property preserved)
- No bring-up performed (plan explicitly stops short of `docker compose up`); single-service `zeeker-datasette` container at `localhost:8001` remains running and healthy

---
*Phase: 02-dual-service-bring-up*
*Plan: 04*
*Completed: 2026-04-21*

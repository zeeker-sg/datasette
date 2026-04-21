---
phase: 03-flip-suffix-based-routing
plan: 02
subsystem: infra
tags: [caddy, reverse-proxy, suffix-routing, single-file-commit, named-matcher, docker]

# Dependency graph
requires:
  - phase: 02-dual-service-bring-up
    provides: "Three-service Docker topology with caddy reverse-proxying everything to zeeker-datasette:8001 and frontend:8000 placeholder reachable internally only"
  - phase: 03-flip-suffix-based-routing/01
    provides: "Verifier scripts (capture_baseline.sh, verify_api_parity.sh) parameterized via ZEEKER_BASELINE_DIR with phase-03-pre default"
provides:
  - "Caddyfile flipped from transparent proxy → datasette into named-`@datasette`-matcher router: *.json|*.csv|*.db|/-/* → zeeker-datasette:8001, everything else → frontend:8000"
  - "On-disk routing contract for REQ-suffix-routing-contract (live behavior activates at Plan 04's `docker compose restart caddy`)"
  - "Single-file commit `ebf3f52` enabling `git revert` rollback to Phase-2 transparent proxy without touching any other source file"
affects: [03-03, 03-04, phase-04-route-porting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Caddy named matcher with two `path` lines OR'd: suffix list (`*.json *.csv *.db`) + prefix glob (`/-/*`) for legibility (vs single combined line)"
    - "Caddy directive auto-sort: matched-handler first in file order, no-matcher catch-all second; Caddy auto-sorts catch-all last regardless"
    - "Validate-but-don't-restart split: Plan 02 mutates+validates the on-disk Caddyfile; Plan 04 owns the `docker compose restart caddy` so the gate is one atomic operation"

key-files:
  created: []
  modified:
    - "Caddyfile - replaced transparent reverse_proxy site block with named `@datasette` matcher + matched-handler + frontend catch-all; updated header comment from Phase 2 → Phase 3 role; removed obsolete `@datasette_api` forward-compat comment block; ran `caddy fmt --overwrite` for tab-style consistency"

key-decisions:
  - "Named matcher `@datasette` (NOT `@datasette_api` from Phase-2 comment sketch) per CONTEXT D-XX — simpler name, locked"
  - "Two `path` lines inside `@datasette` (suffix globs on line 1, `/-/*` prefix on line 2) — functionally identical to one combined line but more legible to reviewers per RESEARCH Anti-Pattern"
  - "No snippet refactor (`(api-routes)` + `import`); no static-asset `respond` short-circuits — both deferred per CONTEXT D-XX"
  - "Ran `caddy fmt --overwrite` to address validator's whitespace warning (tabs not spaces); functional content unchanged"
  - "Did NOT restart Caddy — Plan 04 owns the restart + verifier gate as one atomic operation per CONTEXT and RESEARCH Pattern 4 / Pitfall 2"

patterns-established:
  - "Single-file rollback discipline: `git show --stat HEAD` returns exactly 1 file; rollback is `git revert <hash> && docker compose restart caddy` — no other source file is touched"
  - "Validate-via-Docker-one-shot: `docker run --rm -v ... caddy:2.11.2-alpine caddy validate ...` (same pattern Plan 02-03 used)"

requirements-completed: [REQ-suffix-routing-contract, REQ-incremental-migration]

# Metrics
duration: 2min
completed: 2026-04-21
---

# Phase 03 Plan 02: Flip Caddyfile to suffix-based routing Summary

**Caddyfile flipped from transparent reverse-proxy to named-`@datasette`-matcher suffix router (`*.json|*.csv|*.db|/-/* → zeeker-datasette:8001`, catch-all → `frontend:8000`); validated via Docker-one-shot `caddy validate`; single-file commit so `git revert` is the rollback. Caddy NOT restarted — Plan 04 owns that.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-21T10:02:38Z
- **Completed:** 2026-04-21T10:03:58Z
- **Tasks:** 1
- **Files modified:** 1 (Caddyfile)

## Accomplishments
- Caddyfile content replaced with the locked four-block shape (file-level globals → `:80` site block → `@datasette` matcher → matched-handler → catch-all)
- `caddy validate` passes inside `caddy:2.11.2-alpine` Docker one-shot (line: `Valid configuration`, exit 0)
- Single-file commit `ebf3f52` modifies ONLY `Caddyfile` (`git show --stat HEAD` → 1 file changed, 36 insertions, 29 deletions)
- Live Caddy container untouched — `docker compose ps caddy` still shows `Up 7 hours (healthy)` from the Phase-2 bring-up; on-disk Caddyfile and in-memory Caddy behavior are intentionally out of sync until Plan 04

## Task Commits

1. **Task 1: Flip Caddyfile to suffix-based routing** - `ebf3f52` (feat)

**Plan metadata:** to-be-committed (this SUMMARY + STATE/ROADMAP updates)

## Files Created/Modified
- `Caddyfile` — Replaced transparent `reverse_proxy zeeker-datasette:8001` with named `@datasette` matcher (two `path` lines: `*.json *.csv *.db` and `/-/*`), matched-handler `reverse_proxy @datasette zeeker-datasette:8001`, and catch-all `reverse_proxy frontend:8000`. Header comment updated from Phase-2 transparent-proxy role to Phase-3 suffix-router role. Phase-2 forward-compat comment block (`@datasette_api`) removed (now the actual implementation, no longer dead-code). File-level globals (`auto_https off`, `admin localhost:2019`) preserved verbatim inside the file-level `{ ... }` block. `caddy fmt --overwrite` applied for tab indentation (functional content unchanged).

## Diff applied (before → after)

Before (Phase 2, lines 1-41):
- Header: `Phase 2 of milestone M2 (Frontend / API Split). Role: transparent reverse proxy.`
- Site block: `reverse_proxy zeeker-datasette:8001` (transparent)
- Comment block: `# @datasette_api { path *.json *.csv *.db /-/* } # reverse_proxy @datasette_api zeeker-datasette:8001 # reverse_proxy frontend:8000` (forward-compat sketch)

After (Phase 3, 48 lines):
- Header: `Phase 3 of milestone M2 (Frontend / API Split). Role: suffix-based router. Caddy decides upstream by URL pattern.`
- Site block contains:
  - `@datasette { path *.json *.csv *.db ; path /-/* }` (two-line `path` directive OR'd by Caddy)
  - `reverse_proxy @datasette zeeker-datasette:8001` (matched-handler)
  - `reverse_proxy frontend:8000` (catch-all; Caddy auto-sorts no-matcher last)
- Comment block: GONE (forward-compat became actual implementation)

`git show --stat HEAD`:
```
 Caddyfile | 65 +++++++++++++++++++++++++++++++++++----------------------------
 1 file changed, 36 insertions(+), 29 deletions(-)
```

## `caddy validate` output (verbatim)

```
{"level":"info","ts":1776765793.6794865,"msg":"using config from file","file":"/etc/caddy/Caddyfile"}
{"level":"info","ts":1776765793.6798787,"msg":"adapted config to JSON","adapter":"caddyfile"}
{"level":"info","ts":1776765793.6800387,"logger":"http.auto_https","msg":"automatic HTTPS is completely disabled for server","server_name":"srv0"}
{"level":"info","ts":1776765793.680149,"logger":"tls.cache.maintenance","msg":"started background certificate maintenance","cache":"0x4c2905943d00"}
{"level":"info","ts":1776765793.680178,"logger":"tls.cache.maintenance","msg":"stopped background certificate maintenance","cache":"0x4c2905943d00"}
{"level":"info","ts":1776765793.6801844,"logger":"http","msg":"servers shutting down with eternal grace period"}
Valid configuration
```

Exit code: 0. Validator confirms the routing flip is syntactically correct AND that auto-HTTPS is completely disabled (`auto_https off` honored).

## Acceptance criteria — all 10 PASS

| Check | Result |
|-------|--------|
| `caddy validate` exits 0 with "Valid configuration" | PASS |
| `@datasette {` matcher block opens | PASS |
| `path *.json *.csv *.db` line present | PASS |
| `path /-/*` line present | PASS |
| `reverse_proxy @datasette zeeker-datasette:8001` matched-handler present | PASS |
| `reverse_proxy frontend:8000` catch-all present | PASS |
| No `@datasette_api` leftover from Phase-2 comment | PASS |
| No Phase-2 unconditional `reverse_proxy zeeker-datasette:8001` line | PASS |
| Not using placeholder `datasette:8001` (uses real `zeeker-datasette:8001`) | PASS |
| File-level globals (`auto_https off`, `admin localhost:2019`) preserved | PASS |
| matched-handler appears BEFORE catch-all in file order (awk line-number compare) | PASS |
| Single-file commit: `git show --stat HEAD` shows exactly 1 file, and that file is `Caddyfile` | PASS |

## Decisions Made
- **Ran `caddy fmt --overwrite`:** The first `caddy validate` emitted a `warn` about input-not-formatted (4-space indent vs Caddy's tab convention). Functional content unchanged; tabs vs spaces is whitespace only. Re-validation after `fmt` produced clean output (no warning). The plan's anchored regexes use `\s*` so they pass against either indent style. Optional but worth doing — keeps the file clean for human reviewers.

## Deviations from Plan

None — plan executed exactly as written. The `caddy fmt --overwrite` step is whitespace normalization, not a deviation; the routing semantics, the matcher block, the directive ordering, and the single-file commit discipline all match the plan spec verbatim.

## Issues Encountered

None.

## Caddy live container — NOT restarted (audit trail)

`docker compose ps caddy --format json` confirms:
- `"State":"running"` `"Status":"Up 7 hours (healthy)"` `"RunningFor":"7 hours ago"`
- The container's `CreatedAt: "2026-04-21 11:11:45 +0800"` is the Phase-2 bring-up timestamp; this plan did NOT restart it.

This means: between Plan 03-02's commit and Plan 04's `docker compose restart caddy`, the disk Caddyfile and the live Caddy behavior are out of sync. **This is intentional** — gives the human reviewer a chance to read the diff before activating it. Plan 04 owns the restart + verifier-run gate as one atomic operation.

## Rollback Recipe

If Plan 04 fails the gate or the human checkpoint says "no-ship":

```bash
git revert ebf3f52
docker compose restart caddy
# Caddy reads the reverted Caddyfile (transparent proxy from Phase 2)
# Run verify_phase_02.sh to confirm Phase-2 contract still holds
bash scripts/verify_phase_02.sh
```

This is the entire rollback. Single-file commit discipline (REQ-incremental-migration) means no other source file or topology change needs to be unwound.

## User Setup Required

None — no external service configuration required. The Caddyfile change is local-validation-only per CONTEXT.

## Next Phase Readiness

- **Plan 03-03 (verify_phase_03.sh authoring) — UNBLOCKED:** Wave 3 plan can now author the verifier against the locked Caddyfile shape. Ran in parallel with this plan, but the Caddyfile shape it asserts against is now committed.
- **Plan 03-04 (operator gate: restart caddy + run verifier) — UNBLOCKED:** Wave 4 plan has both inputs in hand:
  - the on-disk Caddyfile in suffix-router shape (from this plan's commit `ebf3f52`)
  - verify_phase_03.sh (from Plan 03-03)
- **Live stack:** Three services still UP and healthy. Plan 04 will run `docker compose restart caddy`, poll for 3/3 healthy, then run `bash scripts/verify_phase_03.sh` followed by `ZEEKER_BASELINE_DIR=.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh`. Both forensic logs will land in `.planning/phases/03-flip-suffix-based-routing/`.

## Self-Check: PASSED

- File `Caddyfile` exists and contains the named `@datasette` matcher (verified via in-session grep checks before commit)
- Commit `ebf3f52` exists in `git log` (verified via `git show --stat HEAD`)
- `caddy validate` returned exit 0 with "Valid configuration" (verbatim output captured above)
- Single-file commit discipline verified: 1 file changed, file is `Caddyfile`
- Caddy container start time unchanged from Phase-2 bring-up (NOT restarted, as required)

---
*Phase: 03-flip-suffix-based-routing*
*Plan: 02*
*Completed: 2026-04-21*

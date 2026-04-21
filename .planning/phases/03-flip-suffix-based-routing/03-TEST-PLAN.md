# Phase 3 — Test Plan (post-flip verification recipe)

Repeatable recipe for verifying or re-verifying the suffix-routing flip.
Use this if Phase 3 needs to be re-validated after a related change
(e.g., Phase 4 deploys a new frontend handler and you want to confirm
the routing contract still holds).

## Preconditions

1. Phase 2 stack running (`docker compose up -d`).
2. Plan 02's Caddyfile committed (`git log --oneline -- Caddyfile` shows
   the suffix-router commit — `ebf3f52` at time of writing).
3. Plan 03's verifier executable (`test -x scripts/verify_phase_03.sh`).
4. Plan 01's parameterized parity script (`grep ZEEKER_BASELINE_DIR
   scripts/verify_api_parity.sh`).
5. Phase-3-pre baselines populated
   (`ls .planning/baselines/phase-03-pre/*.json | wc -l` returns ≥ 13).

## Step 1 — Apply / re-confirm Caddyfile change

The Caddyfile should match Plan 02's locked content (RESEARCH Code
Example 1). Validate:

```bash
docker run --rm \
  -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.11.2-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Expected: `Valid configuration`, exit 0.

## Step 2 — Reload Caddy

ALWAYS prefer `docker compose restart caddy` over `caddy reload`.

```bash
docker compose restart caddy
```

Reason: bind-mounted Caddyfiles are vulnerable to editor-induced inode
swap (atomic-save changes the inode; `caddy reload` may see stale
contents). `restart caddy` re-reads from a fresh container start.

Wait for 3/3 healthy (typically 5-15s):

```bash
until [ "$(docker compose ps --format json | jq -r '.Health // .State' | grep -c '^healthy$')" = "3" ]; do sleep 1; done
```

Sanity-check the bind-mount actually picked up the new Caddyfile:

```bash
docker compose exec caddy grep '@datasette' /etc/caddy/Caddyfile
# Expected: shows the @datasette matcher line.
# If empty: bind-mount is stale → `docker compose down caddy && docker compose up -d caddy`.
```

## Step 3 — Run the automated verifier

```bash
bash scripts/verify_phase_03.sh
```

Sections covered (see Plan 03's authored script for details):
- A. Caddyfile validates
- B. Phase-2 topology invariants (delegated to verify_phase_02.sh)
- C. Positive routing — `*.json`, `*.csv`, `*.db`, `/-/sql`, `/-/search` reach datasette
- D. Negative routing — HTML routes (`/`, `/{db}`, `/{db}/{table}`, etc.)
   return frontend's JSON 404 with body-content fallthrough guard
   (`zeeker-base.css` MUST NOT appear in body)
- E. `/frontend-test` reachability
- F. Edge cases — multi-dot URL with query, HEAD/GET symmetry,
   case-insensitivity, CORS preserved
- G. API byte-parity wrap (auto-exports ZEEKER_BASELINE_DIR=phase-03-pre)

Expected: exit 0, "Phase 3 verifier: ALL GREEN".

On failure, triage using Phase-2's four-category framework (Categories A/B/C/D):
- **Category A** Host base-URL drift (topology-induced; expected if you re-baselined elsewhere)
- **Category B** S3 content drift (metadata.json/plugins.json updated server-side)
- **Category C** Live data freshness drift (row counts, timestamps)
- **Category D** TRUE topology-induced API regression — only this is a no-ship signal

**Known inherited issues (Phase-2 delegation, Section B):**
- `verify_phase_02.sh` check #3 has a known jq false positive documented in
  `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` (EXPOSE-only
  ports with `PublishedPort: 0` misflagged as host-published). Not a Phase-3
  regression.
- `verify_phase_02.sh` check #10 is OBSOLETE post-Phase-3. Check #10 asserts
  "Caddy still routes `/frontend-test` → datasette (404)" which was true pre-flip.
  Post-flip, `/frontend-test` correctly returns 200 from frontend — that's
  Phase 3's point. The check will fail permanently post-Phase-3; it's a
  pre-flip-only assertion and should be retired or inverted in a future
  housekeeping plan.

## Step 4 — Standalone byte-parity check

For the dual-log forensic capture pattern, also run parity standalone:

```bash
ZEEKER_BASELINE_DIR="$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre" \
  bash scripts/verify_api_parity.sh
```

Expected: `REQ-api-byte-parity: PASS`, exit 0 (all 12 baselines byte-identical
to live Caddy-routed responses).

## Step 5 — Manual visual smoke

Open http://localhost/ in a browser (hard-refresh to bypass cache:
Cmd-Shift-R / Ctrl-Shift-R).

- Expected: `{"detail":"Not Found"}` JSON or plain-text FastAPI 404
- **BUG SIGNAL**: page contains `<!DOCTYPE html>`, the datasette
  homepage, or any `zeeker-base.css` link tag → matcher is silently
  fall-through-ing (RESEARCH Pitfall 1)

Open http://localhost/sglawwatch.json in a browser:
- Expected: prettified JSON of the database overview
- BUG signal: 404 from frontend (matcher not catching `*.json`)

Open http://localhost/frontend-test:
- Expected: `{"status":"ok","service":"zeeker-frontend"}`

Open http://localhost/-/sql in a browser:
- Expected: datasette SQL editor HTML (reaches datasette via `/-/*` prefix)
- BUG signal: `{"detail":"Not Found"}` (matcher isn't claiming `/-/*`)

## Step 6 — Rollback (if no-ship)

Single-file commit means rollback is one revert + one restart:

```bash
git revert ebf3f52                   # Plan 02's Caddyfile commit SHA
docker compose restart caddy
bash scripts/verify_phase_02.sh      # confirm rollback worked
```

Expected after rollback: Caddy back to Phase-2 transparent proxy;
`verify_phase_02.sh` passes (modulo its known check-#3 false positive
documented in 02-05-SUMMARY.md and the check-#10 inversion);
`curl http://localhost/sglawwatch` returns datasette HTML again.

If the Plan 02 SHA differs, re-derive it:

```bash
git log --format=%H --max-count=1 -- Caddyfile
```

## Notes

- Phase 3 is local-validation-only; production deploy of suffix routing
  ships in Phase 4 alongside the first ported HTML route (`/`). HTML
  browsing being broken between Phase 3 ship and Phase 4 ship is
  intentional and confined to local dev.
- The Caddyfile's `:80` site block is overlay-compatible: Phase 4's
  `docker-compose.prod.yml` (TBD) will add a `data.zeeker.sg { ... }`
  block alongside, and Caddy will auto-pick the more-specific block per
  request (RESEARCH Pattern 2).
- Future-phase note: if you re-baseline (e.g., Phase 4 captures
  `phase-04-pre/`), update the default in `scripts/verify_api_parity.sh`
  and `scripts/capture_baseline.sh` (both honor `ZEEKER_BASELINE_DIR`
  env var per Plan 01) — or just always pass the env var explicitly.

# Phase 3: Flip suffix-based routing — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** Synthesized from `.planning/intel/` (PRD), `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` (what shipped in Phase 2), and `.planning/baselines/phase-03-pre/` (post-Phase-2 parity reference).

<domain>
## Phase Boundary

Edit the root `Caddyfile` so requests are routed by URL suffix:
- `*.json`, `*.csv`, `*.db`, and `/-/*` → `zeeker-datasette:8001`
- Everything else → `frontend:8000`

Frontend currently only serves `/frontend-test`, so every HTML route a user might hit (`/`, `/sglawwatch`, `/sglawwatch/headlines`, etc.) will return **404 from the frontend** after this flip. That is intentional. Phase 4 starts porting routes (`/`, `/{db}`); Phases 5-6 finish them. During the Phase 3 → Phase 4 window, HTML browsing is broken — the API is fully working and that's what this phase guarantees.

This phase is **local-validation-only**. Do NOT deploy to production. Production deploy ships in Phase 4 along with the first ported HTML route (`/`) so end-users get a usable UI on the same release that the routing changes under them.

This phase does NOT:
- Build any new HTML routes (Phase 4-6).
- Touch `docker-compose.yml` (Phase 2 already shipped the topology).
- Touch the frontend package (Phase 2 scaffolded it; Phase 4 fills it).
- Delete anything from `packages/zeeker-datasette/` (Phase 7).
- Deploy to production.

</domain>

<decisions>
## Implementation Decisions

### The Caddyfile change (single-file edit)
The current Caddyfile has a transparent-proxy site block:
```
:80 {
  reverse_proxy zeeker-datasette:8001
}
```

Phase 3 replaces it with a named-matcher suffix router (per PRD §6):
```
:80 {
  @datasette {
    path *.json *.csv *.db
    path /-/*
  }
  reverse_proxy @datasette zeeker-datasette:8001
  reverse_proxy frontend:8000
}
```

Notes:
- The `path` directive inside `@datasette` is OR'd across multiple invocations — separate path predicates with newlines for the suffix list and a separate line for `/-/*` (a path-prefix match, not a suffix).
- `auto_https off` and `admin localhost:2019` directives stay (they're file-level, not site-level).
- The Phase-3 forward-compat comment block from Phase 2's Caddyfile becomes the actual implementation; the comment can be deleted once the change is made.
- This is a **single-file commit** so `git revert` of the Phase-3 commit returns to Phase-2's transparent proxy without touching anything else.

### The verifier scripts
Phase 2 left three scripts:
- `scripts/capture_baseline.sh` — produces baselines (already re-captured against the post-Phase-2 stack into `.planning/baselines/phase-03-pre/` — this is Phase 3's parity reference).
- `scripts/verify_api_parity.sh` — diffs current `localhost` responses vs baselines. **This script is reusable as-is** for Phase 3 because the API URLs aren't changing — only the routing path inside Caddy is changing.
- `scripts/verify_phase_02.sh` — checks Phase-2 topology assertions. **Adapt to `verify_phase_03.sh`** to additionally assert the suffix-routing behavior:
  - `*.json`, `*.csv`, `*.db`, `/-/*` reach datasette (HTTP 200, content matches baseline)
  - HTML routes that aren't `/frontend-test` return 404 from frontend (NOT 200 from datasette HTML — proves the routing flip worked)
  - `/frontend-test` returns 200 with the placeholder JSON (frontend is reachable)

### Test plan (documented for repeatable post-flip verification)
Author `.planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md` (or similar) listing:
1. Pre-flip command sequence (capture or refresh baselines if needed)
2. Caddyfile edit + reload (`docker compose up -d` to restart Caddy with the new config)
3. Post-flip verification commands (`bash scripts/verify_phase_03.sh`)
4. Rollback command (`git revert <hash>` + `docker compose up -d`)

### REQ-api-byte-parity in Phase 3
Phase 3's parity check uses `.planning/baselines/phase-03-pre/` (NOT the original `phase-02/` baselines). Those were re-captured 2026-04-21 against the post-Caddy stack so the host-base-URL drift that flagged Phase 2's verifier no longer appears.

The Caddy suffix matcher must produce **byte-identical** output for `*.json`, `*.csv`, `*.db`, `/-/*` URLs vs the post-Phase-2 transparent-proxy stack. Caddy is doing the same upstream proxy in both cases (just gated on a path matcher); identical input → identical output is the expectation.

### Negative-routing assertions (the hard part)
After the flip, an HTML request like `curl -fsSI http://localhost/sglawwatch` must return:
- HTTP 404 (from frontend, because no route handler matches `/sglawwatch`)
- NOT HTTP 200 (which would mean the HTML route silently fell through to datasette — a routing bug)

Test this for at least:
- `/` (root)
- `/sglawwatch` (database overview HTML)
- `/sglawwatch/headlines` (table HTML)
- `/sglawwatch/headlines/<rowid>` (row HTML — actual row IDs from the baseline)
- `/-/sql` is `/-/*` — must reach datasette, NOT frontend (positive routing)
- `/-/search` is `/-/*` — must reach datasette
- `/developers` (Datasette plugin route) — must reach frontend = 404 (Phase 6 ports `/developers`)

The negative-routing failure mode the workflow research flagged as a footgun: if Caddy's `path` matcher syntax is wrong (e.g., missing `*` glob), HTML requests might fall through to a default proxy and silently work — passing parity but failing the routing flip. Hence the explicit "must 404" assertions.

### Frontend `/frontend-test` survives
After the flip, the only working frontend route is `/frontend-test`. Verify it still returns the placeholder JSON: `curl http://localhost/frontend-test` → `{"status":"ok","service":"zeeker-frontend"}`.

### Caddy reload pattern
Caddy supports config reload without restart via `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`. This is faster than `docker compose up -d`. Either works; recommend `up -d` for simplicity (it picks up the bind-mounted Caddyfile automatically since the file is mounted, but Caddy doesn't auto-reload — needs an explicit signal).

Actually: Caddy with bind-mounted Caddyfile only reads the file at startup unless told to reload. So either:
- `docker compose restart caddy` (simple, ~3s downtime)
- `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile` (zero downtime)

Phase 3 is local-only with no real users, so `restart caddy` is fine and simpler. Use this in the verifier script.

### Claude's Discretion
- Exact Caddyfile syntax for the named matcher (Caddy supports several equivalent forms).
- Whether to factor out the suffix list into a snippet (Caddy's `(snippet)` syntax) for reuse — recommend NO for this phase; keep it inline so the diff is one place.
- Whether to add a `respond` directive in Caddy to short-circuit obviously-bogus paths instead of proxying (e.g., `/favicon.ico`) — defer to Phase 4 when frontend has a real handler.
- Test-plan documentation file location — recommend `.planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md` per existing convention.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD
- `prd-zeeker-frontend-split.md` — full PRD; this phase implements §10 Step 2 only

### Phase 2 outputs (Phase 3 builds on these)
- `Caddyfile` — current state: transparent proxy. This is what Phase 3 modifies.
- `docker-compose.yml` — three-service topology (datasette, frontend, caddy) — preserved unchanged
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` — frontend FastAPI app (currently only `/frontend-test`)
- `scripts/verify_api_parity.sh` — reusable for Phase 3 parity checks
- `scripts/verify_phase_02.sh` — pattern for Phase 3's adapted verifier
- `scripts/capture_baseline.sh` — already re-captured against post-Caddy stack
- `.planning/baselines/phase-03-pre/` — 13 fresh baselines (post-Caddy, datasette 0.65.2) — the Phase 3 parity reference
- `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` — Phase 2 ship notes including parity triage methodology (Categories A/B/C/D)

### Synthesized Intel
- `.planning/intel/SYNTHESIS.md`
- `.planning/intel/decisions.md` — DEC-2 (suffix-based routing over path-based) directly binds this phase
- `.planning/intel/requirements.md` — REQ-suffix-routing-contract is the headline; REQ-api-byte-parity must continue to hold
- `.planning/intel/constraints.md` — CON-routing-table is the binding contract for this phase

### Caddy reference
- Phase 2's research (`.planning/phases/02-dual-service-bring-up/02-RESEARCH.md`) — Pattern 2 has the Phase-3 suffix matcher snippet; it was deliberately written out as a forward-compat reference for this phase. Re-read it.
- https://caddyserver.com/docs/caddyfile/matchers — official matcher syntax

### CLAUDE.md
- Project instructions; Phase 3 changes the routing layer, not the data layer or template layer — most CLAUDE.md guidance (`metadata.json` is authoritative, `_zeeker_*` tables hidden, CORS enabled, S3 integration) does NOT apply directly. The relevant section: "All API endpoints have CORS enabled" — verify CORS still passes through Caddy after the flip.

</canonical_refs>

<specifics>
## Specific Ideas

### The Caddyfile diff (target shape)

**Before (Phase 2 Caddyfile, current state):**
```
{
  auto_https off
  admin localhost:2019
}

:80 {
  reverse_proxy zeeker-datasette:8001
  # Phase 3 will replace the line above with a suffix-matcher; see:
  # https://caddyserver.com/docs/caddyfile/matchers
}
```

**After (Phase 3 target):**
```
{
  auto_https off
  admin localhost:2019
}

:80 {
  @datasette {
    path *.json *.csv *.db
    path /-/*
  }
  reverse_proxy @datasette zeeker-datasette:8001
  reverse_proxy frontend:8000
}
```

The order matters: matched-handler `reverse_proxy @datasette ...` must come BEFORE the catch-all `reverse_proxy frontend:8000` for Caddy's directive ordering to work correctly.

### Verify_phase_03.sh assertion checklist

Positive routing (must hit datasette):
- `curl -fsS http://localhost/-/versions.json | jq -r .datasette.version` → `0.65.2`
- `curl -fsS http://localhost/sglawwatch.json | jq -r '.tables[0].name'` → expected table name
- `curl -fsS http://localhost/sglawwatch/headlines.json?_size=1 | jq -r '.rows | length'` → `1`
- `curl -fsSI http://localhost/sglawwatch.csv | head -1` → HTTP 200 (CSV download)
- `curl -fsSI http://localhost/sglawwatch.db | head -1` → HTTP 200 (sqlite db download)
- `curl -fsSI http://localhost/-/sql | head -1` → HTTP 200 (SQL editor — datasette HTML, but it's `/-/*` so it routes to datasette in Phase 3)

Negative routing (must hit frontend = 404):
- `curl -fsSI -o /dev/null -w "%{http_code}" http://localhost/` → `404`
- `curl -fsSI -o /dev/null -w "%{http_code}" http://localhost/sglawwatch` → `404` (not 200 — would mean fallthrough)
- `curl -fsSI -o /dev/null -w "%{http_code}" http://localhost/sglawwatch/headlines` → `404`
- `curl -fsSI -o /dev/null -w "%{http_code}" http://localhost/developers` → `404`

Frontend reachability:
- `curl -fsS http://localhost/frontend-test` → `{"status":"ok","service":"zeeker-frontend"}`

API parity (reuse Phase 2's verifier with the new baselines):
- `bash scripts/verify_api_parity.sh` against `.planning/baselines/phase-03-pre/` → exit 0 with empty diff

Negative-fallthrough trap (the load-bearing one):
- `curl -fsS http://localhost/sglawwatch | grep -i 'datasette\|sql\|table' && echo "FALLTHROUGH BUG" || echo "OK 404"` — if datasette HTML is served on `/sglawwatch`, the routing flip is broken even if everything else "works"

### Test plan doc structure

Suggested `03-TEST-PLAN.md` outline:
1. Preconditions (Phase 2 stack running; baselines at `.planning/baselines/phase-03-pre/`)
2. Apply the Caddyfile change
3. Reload Caddy (`docker compose restart caddy`)
4. Run `bash scripts/verify_phase_03.sh`
5. Manual visual check (open `http://localhost/` in browser → expect 404; open `http://localhost/sglawwatch.json` → expect JSON)
6. Rollback: `git revert <commit-hash> && docker compose restart caddy`

</specifics>

<deferred>
## Deferred Ideas

- Production deploy of the suffix routing — Phase 4 (deploys with the first ported HTML route).
- Frontend route handlers (`/`, `/{db}`, etc.) — Phase 4-6.
- Caddy snippet refactoring — defer; keep it inline for diff clarity.
- `respond` directives for static-asset short-circuits (favicon, robots.txt, etc.) — Phase 4 or later.
- Re-baseline against post-Phase-3 stack for Phase 4's parity reference — that's a Phase 4 task.

</deferred>

---

*Phase: 03-flip-suffix-based-routing*
*Context gathered: 2026-04-21 from `.planning/intel/` + Phase 2 outputs*

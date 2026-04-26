# Phase 3: Flip suffix-based routing — Research

**Researched:** 2026-04-21
**Domain:** Caddy v2 named matchers + path globbing; multi-handler `reverse_proxy` ordering; bind-mount Caddyfile reload mechanics; negative-routing assertion patterns; reusing Phase-2 verifier scripts against re-baselined references
**Confidence:** HIGH (all Caddy semantics verified against caddyserver.com/docs 2026-04-21; current stack live-probed for empirical edge cases)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**The Caddyfile change (single-file edit).** Replace the Phase-2 transparent-proxy site block with a named-matcher suffix router (per PRD §6):

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

**Verifier scripts:**
- `scripts/capture_baseline.sh` — already produced `.planning/baselines/phase-03-pre/` (the Phase 3 parity reference).
- `scripts/verify_api_parity.sh` — **reusable** for Phase 3 because the API URLs are unchanged. (Caveat: see "Decisions Phase 3 must address" below — its `BASELINE_DIR` is hardcoded to `phase-02`.)
- `scripts/verify_phase_02.sh` — **adapt to `verify_phase_03.sh`** with positive-routing, negative-routing, and frontend-reachability assertions.

**Test plan documented.** Author `.planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md` listing pre-flip → edit → reload → verify → rollback.

**REQ-api-byte-parity in Phase 3.** Diff against `.planning/baselines/phase-03-pre/` (NOT the original `phase-02/`). Caddy is doing the same upstream proxy in both topologies — just gated on a path matcher — so output must be byte-identical for the routes covered by `@datasette`.

**Negative-routing assertions are the load-bearing test.** After the flip, an HTML request like `curl -fsSI http://localhost/sglawwatch` MUST return 404 (from frontend) and MUST NOT return 200 (which would mean fallthrough to datasette HTML — a routing bug masquerading as success). Test for at least: `/`, `/sglawwatch`, `/sglawwatch/headlines`, `/sglawwatch/headlines/<rowid>`, `/-/sql` (positive — must reach datasette), `/-/search` (positive — must reach datasette), `/developers` (negative — must reach frontend = 404).

**Frontend `/frontend-test` survives.** `curl http://localhost/frontend-test` → `{"status":"ok","service":"zeeker-frontend"}`.

**Caddy reload pattern.** Either `docker compose restart caddy` (~3s downtime, simple) or `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile` (zero-downtime). Phase 3 is local-only with no real users → use `docker compose restart caddy` in the verifier script.

### Claude's Discretion

- Exact Caddyfile syntax for the named matcher (Caddy supports several equivalent forms — research below picks the simplest correct one).
- Whether to factor out the suffix list into a snippet (Caddy's `(snippet)` syntax) — recommend NO; keep inline so the diff is one place.
- Whether to add a `respond` directive to short-circuit obviously-bogus paths (`/favicon.ico`) — defer to Phase 4.
- Test-plan file location — recommend `.planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md`.

### Deferred Ideas (OUT OF SCOPE — Phase 3 must NOT touch these)

- Production deploy of the suffix routing — Phase 4 (deploys with the first ported HTML route).
- Frontend route handlers (`/`, `/{db}`, etc.) — Phase 4–6.
- Caddy snippet refactoring — defer; keep inline for diff clarity.
- `respond` directives for static-asset short-circuits — Phase 4 or later.
- Re-baseline against post-Phase-3 stack for Phase 4's parity reference — that's a Phase 4 task.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-suffix-routing-contract | Caddy reverse proxy routes by URL suffix: `*.json`, `*.csv`, `*.db`, `/-/*` → datasette; everything else → frontend. Suffix matching only — no path-prefix routing. | Standard Stack → Caddyfile (verified syntax); Architecture Patterns → Pattern 1 (named matcher with path); Validation Architecture → positive + negative routing test matrix. |
| REQ-api-byte-parity | Every `.json`, `.csv`, `.db`, `/-/*` URL returns identical bytes pre/post (modulo timestamps + version strings). | Reuses `scripts/verify_api_parity.sh` against `.planning/baselines/phase-03-pre/` — those 12 baselines were captured on the post-Phase-2 (post-Caddy) stack so host-base-URL drift is gone. See "Decisions Phase 3 must address" for the one script edit needed. |
| REQ-incremental-migration | Single-file commit so `git revert` is the rollback. | Caddyfile is the only file Phase 3 mutates; rollback is `git revert <hash> && docker compose restart caddy`. Verified by directive-ordering research: catch-all `reverse_proxy frontend:8000` is auto-sorted last by Caddy regardless of file position, so the diff is "delete one line, add four" with no other source-file ripple. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No hardcoded database references** — Phase 3 introduces nothing database-specific. The Caddyfile matcher is generic suffix/prefix; `*.json` matches every database's tables identically.
- **All API endpoints have CORS enabled** — datasette's `--cors` flag is preserved (set in `entrypoint.sh`, untouched by Phase 3). Caddy by default forwards response headers verbatim, so CORS headers continue to reach clients via the proxy. Verification recipe in Validation Architecture.
- **Three-pass merge / S3 download / metadata.json / self-hosted fonts / `_zeeker_*` hidden tables** — all unaffected by a routing-layer change. Phase 3 touches only how Caddy decides which upstream to hit.

## Summary

Phase 3 is **one Caddyfile edit**. The shape is exactly what Phase 2's Caddyfile carries as a comment-block forward-compat sketch. The risk surface is small but unforgiving:

1. **Caddy's `path` matcher semantics are exactly right for our needs** — verified against [caddyserver.com/docs/caddyfile/matchers](https://caddyserver.com/docs/caddyfile/matchers): `*.json` is a "suffix match," multiple paths in a single `path` directive are OR'd, multiple `path` lines inside the same named matcher are also OR'd, paths are normalized (URL-decoded, multiple slashes merged), case-insensitive, and query strings are ignored. Every edge case in the orchestrator brief is the safe outcome.

2. **Caddy auto-sorts `reverse_proxy @matcher ...` before `reverse_proxy fallback`** — file ordering doesn't matter; the catch-all (no matcher) is sorted last by Caddy regardless. We still write matched-first → catch-all-second for human readability and to match the PRD's own snippet.

3. **The big footgun is silent fallthrough.** If the matcher is misspelled (e.g., `path .json` without the `*`), datasette HTML may continue to be served on `/sglawwatch` and parity will pass while routing is silently broken. Mitigation: explicit negative-routing assertions that grep response bodies for `zeeker-base.css` (the unique datasette-rendered-HTML fingerprint — verified live against the current stack).

4. **`scripts/verify_api_parity.sh` and `scripts/capture_baseline.sh` both hardcode `phase-02` as the baseline directory.** The Phase-3 baselines live in `phase-03-pre`. Phase 3's plan must either (a) update the verifier's `BASELINE_DIR` to point to `phase-03-pre`, or (b) parameterize via env var and pass it from the new `verify_phase_03.sh`. Recommend (b) — keeps the script reusable for future phases.

5. **Bind-mount Caddyfile reload has a known inode-swap gotcha.** Editors that rewrite the file (vim with `:w`, some IDEs) change the inode and the bind-mount can stop seeing updates. The safe pattern is `docker compose restart caddy` for the verifier (re-reads the file at startup). Zero-downtime `caddy reload` works too but inherits the inode risk.

**Primary recommendation:** Write the four-line replacement exactly as the PRD/CONTEXT specifies, validate with `docker run --rm -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` (same pattern Phase 2 used), reload via `docker compose restart caddy`, and run the new `scripts/verify_phase_03.sh` which combines positive routing, negative routing (with body-content fallthrough guards), frontend-reachability, and parameterized parity diff against `phase-03-pre`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| URL suffix matching (`*.json`, `*.csv`, `*.db`) | Caddy (proxy) | — | DEC-2 / CON-routing-table: routing is the proxy's job, not the backends'. Suffix glob is a first-class Caddy `path` matcher feature. |
| URL prefix matching (`/-/*`) | Caddy (proxy) | — | Same matcher block; Caddy's `path` directive natively supports both suffix (`*.json`) and prefix (`/prefix/*`) globs in the same predicate list. |
| Default routing (everything else → frontend) | Caddy (proxy) | — | The catch-all `reverse_proxy frontend:8000` directive (no matcher) — Caddy auto-sorts it last. |
| Data API responses (`.json`/`.csv`/`.db`/`/-/*`) | Datasette (backend) | — | DEC-1: keep datasette as API backend; Phase 3 only changes which Caddy directive hits it, not what it returns. |
| HTML 404s (post-flip) | Frontend (FastAPI) | — | After the flip, frontend's default 404 (`{"detail":"Not Found"}` JSON) replaces datasette's branded HTML 404. This is intentional and is the empirical signal the routing flipped. |
| `/frontend-test` reachability | Frontend (FastAPI) | — | The single existing frontend route. Post-flip it MUST return 200 with placeholder JSON; pre-flip it returns 404 (datasette). |
| TLS / public exposure | Caddy (proxy) | — | Unchanged from Phase 2. |
| Internal service discovery | Compose default bridge network DNS | — | Unchanged. `zeeker-datasette` and `frontend` resolve by service name. |

## Standard Stack

### Core (Caddyfile syntax — the only "stack" change in Phase 3)

| Construct | Purpose | Why standard |
|-----------|---------|--------------|
| Named matcher `@datasette { ... }` | Define a reusable predicate set; reference it from `reverse_proxy @datasette ...` | Per [Caddyfile matchers docs](https://caddyserver.com/docs/caddyfile/matchers): "Named matchers are defined outside of any particular directive and can be reused, giving you more flexibility to combine any available matchers into a set." [VERIFIED: caddyserver.com/docs/caddyfile/matchers, fetched 2026-04-21] |
| `path *.json *.csv *.db` | Match any request whose URI path ends in `.json`, `.csv`, or `.db` | Caddy docs: `path` matches "the path component of the request URI" using globs; `*.suffix` is "for a suffix match"; "Multiple paths will be OR'ed together." [VERIFIED: caddyserver.com/docs/caddyfile/matchers] |
| `path /-/*` | Match any request whose URI path starts with `/-/` | Caddy docs: `/prefix/*` is "for a prefix match." [VERIFIED] |
| Two `path` lines inside the same `@datasette` block | OR the suffix list with the prefix predicate | Multiple `path` invocations inside one named matcher are OR'd. [VERIFIED: caddyserver.com/docs/caddyfile/matchers — "Multiple paths will be OR'ed together"] |
| `reverse_proxy @datasette zeeker-datasette:8001` | Forward matched requests to the datasette backend | Standard `reverse_proxy` form; the named matcher is the first positional argument. [VERIFIED: caddyserver.com/docs/caddyfile/directives/reverse_proxy] |
| `reverse_proxy frontend:8000` (no matcher) | Catch-all for everything else | Caddy auto-sorts directives so "A directive with no matcher (matching all requests) is sorted last." [VERIFIED: caddyserver.com/docs/caddyfile/directives — sorting rules] |

### Image / runtime versions (unchanged from Phase 2)

| Image | Tag | Purpose | Status |
|-------|-----|---------|--------|
| `caddy` | `2.11.2-alpine` | Reverse proxy | Pinned in Phase 2; no change. |

[VERIFIED: docker-compose.yml line 69 confirms current pin; live `docker compose ps` shows `caddy:2.11.2-alpine` running healthy at 2026-04-21T07:00Z]

### Alternatives Considered (Caddyfile expression of the same matcher)

| Instead of (chosen) | Could use | Tradeoff | Decision |
|---------------------|-----------|----------|----------|
| `@datasette { path *.json *.csv *.db; path /-/* }` (two-line block) | `@datasette path *.json *.csv *.db /-/*` (single inline line) | Inline is one line shorter. The CONTEXT-locked block-form is slightly more readable and matches the PRD's snippet exactly. | **Block-form (locked).** Matches CONTEXT verbatim; reviewer sees the suffix list and the prefix as separate intents. |
| `path *.json *.csv *.db /-/*` (mix suffixes + prefix in one `path` line) | (alternative form) | Functionally identical (all OR'd). | **Use the locked two-line block.** Same outcome; CONTEXT-locked layout. |
| `path` matcher | `path_regexp` (regex) | `path_regexp` is more powerful but harder to read; suffixes/prefix don't need regex; introduces capture-group complexity. | **`path` matcher.** Simpler; case-insensitive by default which matches what we want. |
| Named matcher `@datasette` | `handle` blocks (`handle @api { ... }` / `handle { ... }`) | `handle` blocks are mutually exclusive (only one fires per request). Two `reverse_proxy` directives also are mutually exclusive given Caddy's auto-sort: matched first, catch-all last. The `handle` form is more verbose for our 1-handler-per-branch case. | **Named matcher + two `reverse_proxy`.** Matches the PRD snippet; less indentation than `handle`. |
| Inline matcher per directive | Snippet (`(api-routes) { ... }` + `import api-routes`) | Snippet wins when the matcher is reused across multiple sites. Phase 3 has one site block; reuse is hypothetical. CONTEXT explicitly recommends NO snippet. | **Inline.** One place to read the routing contract. |

**Caddyfile installation:** No new packages — `caddy:2.11.2-alpine` is already pulled and running.

**Validation command (mirrors Phase 2's pattern, verified working in `02-03-SUMMARY.md`):**

```bash
docker run --rm \
  -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.11.2-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Expected output: `Valid configuration`, exit 0.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────────┐
                    │  HOST  (developer laptop)            │
                    │                                       │
   curl http://     │   :80                                 │
   localhost/...  ──┼─►┌──────────────────┐                 │
                    │  │  caddy (public)  │                 │
                    │  │  caddy:2.11.2-   │                 │
                    │  │  alpine          │                 │
                    │  └────────┬─────────┘                 │
                    │           │                           │
                    │  ┌────────▼─────────┐                 │
                    │  │  @datasette      │                 │
                    │  │  matcher fires?  │                 │
                    │  │                  │                 │
                    │  │  path matches    │                 │
                    │  │   *.json|*.csv|  │                 │
                    │  │   *.db|/-/*      │                 │
                    │  └─┬──────────────┬─┘                 │
                    │    │ YES          │ NO                │
                    │    ▼              ▼                   │
                    │  ┌──────────┐   ┌───────────┐         │
                    │  │datasette │   │ frontend  │         │
                    │  │ :8001    │   │ :8000     │         │
                    │  │ → API    │   │ →         │         │
                    │  │   responds│   │ /frontend-│        │
                    │  │   200/200│   │   test 200 │        │
                    │  │   (JSON  │   │ everything │        │
                    │  │   /CSV/  │   │ else 404   │        │
                    │  │   .db)   │   │ (FastAPI   │        │
                    │  │          │   │ default)   │        │
                    │  └──────────┘   └───────────┘         │
                    └───────────────────────────────────────┘

Trace: a `.json` request enters Caddy → @datasette matcher's `path *.json` is evaluated (OR'd against `*.csv`, `*.db`, then OR'd against the `/-/*` prefix) → matches → `reverse_proxy @datasette zeeker-datasette:8001` fires → datasette returns identical bytes to today.

Trace: an HTML request `/sglawwatch` enters Caddy → @datasette matcher's predicates do NOT match (no .json/.csv/.db suffix; doesn't start with `/-/`) → catch-all `reverse_proxy frontend:8000` fires → frontend has no handler for `/sglawwatch` → FastAPI returns `404 {"detail":"Not Found"}`. This is the success state.

Failure mode (silent fallthrough): if the matcher syntax is wrong (e.g., `path .json` missing the `*`), the matcher never matches → catch-all sends EVERYTHING to frontend → `.json` URLs return 404 from frontend → parity check is decisively red. If the matcher is wrong in the OPPOSITE direction (e.g., `path *` matches everything), HTML routes return datasette HTML and parity passes. Verification must guard against both directions — see Validation Architecture.
```

### Component Responsibilities

| Component | Path in repo | Responsibility | Phase 3 status |
|-----------|--------------|----------------|----------------|
| `Caddyfile` | repo root | Three-line site-block body changes from "everything → datasette" to "matched → datasette, else → frontend" | **EDITED in Phase 3** |
| `docker-compose.yml` | repo root | Three-service topology | UNCHANGED |
| `packages/zeeker-frontend/src/zeeker_frontend/main.py` | sub-package | `/frontend-test` only | UNCHANGED (Phase 4 adds routes) |
| `scripts/verify_phase_02.sh` | scripts/ | Phase 2 verifier | UNCHANGED — used as the structural template for `verify_phase_03.sh` |
| `scripts/verify_api_parity.sh` | scripts/ | Parity diff vs baselines | **EDITED** to parameterize `BASELINE_DIR` (currently hardcoded to `phase-02`) |
| `scripts/verify_phase_03.sh` | scripts/ | NEW — positive routing + negative routing + frontend reachability + parity wrap | **NEW in Phase 3** |
| `.planning/baselines/phase-03-pre/` | planning | Phase-3 parity reference (12 JSON + 12 .url files) | EXISTS — captured 2026-04-21 against post-Phase-2 stack (verified by directory listing) |
| `.planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md` | planning | Repeatable post-flip verification recipe | **NEW in Phase 3** |

### Recommended Project Structure (deltas only)

```
zeeker-datasette/
├── Caddyfile                                       # EDITED (3-line body → 4-line block)
├── scripts/
│   ├── verify_phase_02.sh                          # UNCHANGED (left as historical artifact)
│   ├── verify_phase_03.sh                          # NEW — Phase 3 verifier
│   ├── verify_api_parity.sh                        # EDITED (parameterize BASELINE_DIR)
│   └── capture_baseline.sh                         # UNCHANGED (already used to produce phase-03-pre/)
├── .planning/
│   ├── baselines/phase-03-pre/                     # EXISTS (12 JSON + 12 .url files)
│   └── phases/03-flip-suffix-based-routing/
│       ├── 03-CONTEXT.md                           # EXISTS
│       ├── 03-RESEARCH.md                          # this file
│       └── 03-TEST-PLAN.md                         # NEW (per CONTEXT)
└── (everything else UNCHANGED)
```

### Pattern 1: Named matcher with mixed suffix + prefix predicates

**What:** Define a single named matcher containing two `path` directives — one with a list of suffix globs, another with a prefix glob. Reference it from a `reverse_proxy` directive. Provide a no-matcher `reverse_proxy` as the catch-all.

**When to use:** Multi-backend reverse proxy where the routing rules combine "ends with X" and "starts with Y" predicates.

**Example (the Phase-3 Caddyfile in full):**

```caddyfile
# zeeker-datasette — root Caddyfile
#
# Phase 3 of milestone M2 (Frontend / API Split).
# Role: suffix-based router. Caddy decides upstream by URL pattern.
#
#   *.json | *.csv | *.db | /-/*   ──►  zeeker-datasette:8001 (data API)
#   everything else                ──►  frontend:8000 (HTML; mostly 404 until Phase 4-6)
#
# Source: caddyserver.com/docs/caddyfile/matchers ("Multiple paths will be
#   OR'ed together"; *.suffix = "suffix match"; /prefix/* = "prefix match")
# Used by: docker-compose.yml caddy service, volume-mounted at
#   /etc/caddy/Caddyfile:ro
# DNS: relies on Compose's default project bridge network resolving
#   `zeeker-datasette` and `frontend` to container IPs.

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

[VERIFIED matcher semantics: caddyserver.com/docs/caddyfile/matchers, fetched 2026-04-21]
[VERIFIED auto-sorting: caddyserver.com/docs/caddyfile/directives — "A directive with no matcher (matching all requests) is sorted last"]

### Pattern 2: Production-overlay-safe site address

The Phase-3 Caddyfile uses `:80 { ... }` (port-only). This was a deliberate Phase-2 choice and Phase 3 preserves it because the production overlay (`docker-compose.prod.yml`, future) will add **another** site block keyed by hostname (e.g., `data.zeeker.sg { ... }`) and Caddy will auto-pick the more-specific block per request.

**Forward-compat sketch (NOT in Phase 3 — informs the layout):**

```caddyfile
# Production overlay (hypothetical Phase-4 docker-compose.prod.yml mounts an
# overlay Caddyfile that ADDS the hostname site block alongside the :80 block):

data.zeeker.sg {
    @datasette {
        path *.json *.csv *.db
        path /-/*
    }
    reverse_proxy @datasette zeeker-datasette:8001
    reverse_proxy frontend:8000
}

# The :80 block stays as a local-dev fallback or is dropped from the overlay.
```

The Phase-3 routing rules are reusable verbatim in the production block — nothing to redo. **Production-overlay compatibility is preserved by Phase 3's design.**

### Pattern 3: Caddyfile validation (Docker, no host caddy install required)

**What:** Run `caddy validate` inside a one-shot container that volume-mounts the Caddyfile. Same pattern Phase 2 used in plan 02-03.

**Example:**

```bash
docker run --rm \
  -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.11.2-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

Expected: `Valid configuration`, exit 0. Run BEFORE reload — validation is cheap and catches typos before they take down the proxy.

[VERIFIED: caddyserver.com/docs/command-line — "validate ... deserializes the config, then loads and provisions all of its modules as if to start the config" — provides "stronger error check than merely serializing a config as JSON"]

### Pattern 4: Caddy reload mechanics (bind-mounted Caddyfile)

Caddy doesn't auto-reload bind-mounted Caddyfiles. Two options:

**Option A — restart the container (simple, ~3s downtime):**
```bash
docker compose restart caddy
```
Caddy re-reads the file at startup. Downtime is the container restart window (typically 1-3s including healthcheck stabilization).

**Option B — graceful reload (zero downtime):**
```bash
docker compose exec -w /etc/caddy caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```
Note `-w /etc/caddy` working-directory flag — recommended pattern from the caddy-docker community to avoid path issues. Caddy uses its admin endpoint (bound at `localhost:2019` per our Caddyfile) to swap config in-memory.

[VERIFIED: caddyserver.com/docs/command-line — "the correct, semantic way to change/reload the running configuration"; "the admin endpoint must not be disabled"]

**Bind-mount inode gotcha (verified from caddy-docker GitHub issue #364):** Editors that rewrite the file (vim with `:w`, some IDEs) change the file's inode. Docker bind-mounts of single files are pinned to inode at container-start time, so the new contents may not appear inside the container until restart. **Phase 3 mitigation:** use `docker compose restart caddy` in the verifier — it sidesteps inode swap entirely (the container starts fresh and re-reads the bind-mount).

[VERIFIED via WebSearch: github.com/caddyserver/caddy-docker/issues/364 + community caddy.community/t/27308]

### Anti-Patterns to Avoid

- **Writing the catch-all FIRST in the file thinking it'll shadow the matcher.** Caddy auto-sorts; file order is a human-readability convenience only. We still write `reverse_proxy @datasette ...` before `reverse_proxy frontend:8000` for clarity.
- **Using a single `path` line that mixes suffix + prefix glob with awkward escaping.** E.g., `path *.json *.csv *.db /-/*` works but reviewers may misread `/-/*` as a suffix. Two `path` lines (one for suffixes, one for the prefix) is more legible AND functionally identical.
- **Forgetting the `*` in suffix globs.** `path .json` matches the literal path `/.json` only — NOT `/sglawwatch/headlines.json`. The `*.json` glob is what makes "ends with .json" work. The `caddy validate` step won't catch this — it's syntactically valid; semantically wrong. Negative-routing assertions are the safety net.
- **Probing only with happy-path URLs.** `curl http://localhost/sglawwatch.json` returning 200 is necessary but not sufficient — it could pass even if the catch-all is wrong. Negative-routing probes (HTML routes MUST return frontend's JSON 404, not datasette's HTML 404) are what make the gate honest.
- **Using `Server` header to detect the upstream.** Both datasette (uvicorn-based) and frontend (FastAPI on uvicorn) emit `Server: uvicorn`. [VERIFIED live 2026-04-21 — `curl -I http://localhost/sglawwatch.db` returned `Server: uvicorn`.] Use **body-content sniffing** instead: datasette HTML 404 contains the string `zeeker-base.css` (the static asset reference); frontend's 404 is `{"detail":"Not Found"}` JSON. These are unmistakable.
- **Reloading via `caddy reload` after editing with vim.** Vim's atomic-save changes the file inode; bind-mount may show stale content. Use `docker compose restart caddy` in scripts; humans editing interactively can use either, but should verify with `docker compose exec caddy cat /etc/caddy/Caddyfile | head` before reload.
- **Pointing `verify_api_parity.sh` at `phase-02/`.** That directory was renamed to `phase-03-pre/` (commit `ee3f3ad`). The script must be updated, OR the verifier must pass `BASELINE_DIR` via env var. Recommend the env-var route — keeps the script reusable for Phase 4+.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL pattern matching for the proxy | A regex-based router or a sidecar nginx | Caddy's `path` matcher with `*.suffix` + `/prefix/*` globs | First-class Caddy feature; automatic OR semantics; case-insensitive; query-string-agnostic; URL-decoded normalization built in |
| Directive ordering ("matched first, catch-all last") | Manually sorting directives in the file | Caddy's auto-sort | Caddy sorts same-named directives by matcher specificity; catch-all is always last per [docs](https://caddyserver.com/docs/caddyfile/directives) |
| Negative-routing assertion (proving HTML doesn't fall through) | Inspecting Caddy's debug log | `curl ... | grep -qi 'zeeker-base.css'` body sniff | The proxy's job is to do the right thing silently; inspecting logs is observation, not verification. Body-content grep is a behavioral test. |
| Caddyfile syntax check | A custom Python parser | `caddy validate` (one-shot Docker container) | Caddy's own parser is the only authoritative one; using anything else risks divergence. Phase 2 already proved this works (plan 02-03 SUMMARY). |
| Caddy graceful reload | Sending SIGHUP / SIGUSR1 by hand | `caddy reload --config ... --adapter caddyfile` (or `docker compose restart caddy`) | `caddy reload` is "the correct, semantic way" per official docs. SIGHUP works on some Caddy builds but isn't documented. |
| Parity verification | Re-implementing diff logic | `scripts/verify_api_parity.sh` (already exists, just needs the BASELINE_DIR redirect) | Phase 2 already wrote this, including the `jq` strip filter for volatile fields. Reusing it is the entire point of having scripted Wave-0 verifiers. |

**Key insight:** Phase 3 is a one-line conceptual change ("add a path matcher and a fallback handler") with all the heavy lifting already done by Caddy and by Phase 2's verifier scripts. The novelty in Phase 3 is **negative-routing assertions** — proving the matcher fires on the right inputs AND doesn't fire on the wrong ones. That's the only thing Phase 2's verifier doesn't already do, because Phase 2's whole point was "Caddy routes 100% to datasette."

## Common Pitfalls

### Pitfall 1: Silent fallthrough — matcher misspelled, HTML routes still serve datasette HTML

**What goes wrong:** You write `path .json` instead of `path *.json` (typo: missing `*`). The matcher never matches. By Caddy's auto-sort, requests fall through to the catch-all `reverse_proxy frontend:8000`. Now `.json` requests return 404 from frontend (loud failure — verify_api_parity will scream).

**The reverse failure is sneakier:** you write `path *` (matches everything). All requests go to datasette. HTML requests return datasette-rendered HTML. The user-facing site looks fine. Parity passes. **The Phase-3 routing flip is silently inactive.**

**Why it happens:** `caddy validate` exits 0 — the syntax is fine, the semantics are wrong. There's no schema-level guard against "your matcher matches the wrong things."

**How to avoid:** Negative-routing assertions in `verify_phase_03.sh` MUST sniff response bodies, not just status codes. The decisive guard:

```bash
curl -s http://localhost/sglawwatch | grep -qi 'zeeker-base.css' && {
    echo "FALLTHROUGH BUG: HTML route is being served by datasette" >&2
    exit 1
}
```

`zeeker-base.css` appears in every datasette-rendered HTML page (header `<link>` tag — verified live 2026-04-21). Frontend's 404 (`{"detail":"Not Found"}` JSON) does not contain it.

**Warning signs:** Status codes look right but the page renders the old design language. `docker compose logs caddy | tail -20` shows requests routing to `zeeker-datasette:8001` for paths that should go to frontend.

### Pitfall 2: Bind-mount inode swap — Caddy doesn't see the new Caddyfile

**What goes wrong:** You edit the Caddyfile, `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`. The reload exits 0. Behavior is unchanged.

**Why it happens:** Some editors (vim's atomic save, certain IDE patterns) write to a temp file then rename it over the original. The new file has a different inode. Docker's single-file bind-mount is inode-pinned at container-start; the inside-container view of the file is stale.

[VERIFIED: github.com/caddyserver/caddy-docker/issues/364]

**How to avoid:**
1. Use `docker compose restart caddy` in scripts (re-reads file fresh).
2. If interactively reloading, first verify: `docker compose exec caddy cat /etc/caddy/Caddyfile | grep '@datasette'`. If you see the OLD content, the bind-mount is stale → `docker compose restart caddy`.
3. Optionally configure your editor to write-in-place (vim: `:set backupcopy=yes`).

**Warning signs:** Verifier script runs `caddy reload` then immediately fails with "behavior didn't change." Adding a `cat /etc/caddy/Caddyfile` debug line before reload reveals the stale view.

### Pitfall 3: `verify_api_parity.sh` points at `phase-02/` not `phase-03-pre/`

**What goes wrong:** The verifier script silently uses Phase-2 baselines (which still exist in `git log` but the directory was renamed to `phase-03-pre` in commit `ee3f3ad`). With the rename, the directory `phase-02/` no longer exists, so the verifier fails fast with "no baselines found in .../phase-02" — which IS visible. Good. But if a future contributor unrenames or recreates `phase-02/`, drift is silent.

**Why it happens:** Hardcoded path in `scripts/verify_api_parity.sh` line 10: `BASELINE_DIR="...phase-02"`.

**How to avoid:** Phase 3's plan must edit the verifier to either:
- (a) Hardcode the new value: `BASELINE_DIR="...phase-03-pre"`. Simple, single-purpose, but every future phase will need to re-edit.
- (b) Parameterize: `BASELINE_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"`. Gives env-var override; default tracks the current phase.

**Recommendation:** option (b). The new `verify_phase_03.sh` then exports `ZEEKER_BASELINE_DIR=$ROOT/.planning/baselines/phase-03-pre` before invoking parity, and Phase 4 can do the same with `phase-04-pre` without further script edits.

**Same fix needed in `scripts/capture_baseline.sh`** (line 13) — same hardcoded `phase-02` path. Phase 3 can leave it (capture isn't run in Phase 3) but documenting the future fix is worth a line in the test plan.

**Warning signs:** Verifier exits with `ERROR: no baselines found in .../phase-02` even though `.planning/baselines/phase-03-pre/` is populated.

### Pitfall 4: `/-/*` matcher accidentally catches `/-/sql` AND a hypothetical future `/-/health` frontend route

**What goes wrong:** Someone adds a frontend route at `/-/health` for monitoring. After Phase 3's flip, `/-/*` matches it → routes to datasette → 404 from datasette (no such route).

**Why it happens:** The `/-/*` prefix is reserved by Datasette historically, but it's a convention not a contract. A frontend developer might assume `/-/` is generally available.

**How to avoid:** Document in the Caddyfile comment that `/-/*` is the datasette-reserved prefix and frontend MUST NOT use it. Phase 3 doesn't need to enforce this further — there's no `/-/*` frontend route today. Flag for Phase 4-6 docs.

**Warning signs:** A frontend `/-/anything` route 404s from datasette in production.

### Pitfall 5: Browser caching of the old datasette HTML 404

**What goes wrong:** You open `http://localhost/sglawwatch` in a browser pre-flip → datasette renders the table HTML. You flip Phase 3, restart Caddy. You re-open `http://localhost/sglawwatch` → browser shows the OLD page (cache).

**Why it happens:** Datasette's responses include cache headers; some browsers cache aggressively even on `Cache-Control: max-age=0` responses for back/forward navigation.

**How to avoid:** Phase 3's manual smoke check should use a hard refresh (Cmd-Shift-R / Ctrl-Shift-R) or a curl-based check. The automated verifier uses `curl` exclusively → not affected.

**Warning signs:** `curl http://localhost/sglawwatch` returns frontend's JSON 404 but the browser still shows the datasette HTML page. Solution: hard refresh.

### Pitfall 6: HEAD vs GET asymmetry

**What goes wrong:** `curl -I http://localhost/sglawwatch.json` (HEAD) returns one status; `curl http://localhost/sglawwatch.json` (GET) returns another. Verifier script uses HEAD for some assertions and GET for others; results disagree.

**Why it happens:** Caddy's `path` matcher is method-agnostic (matches on URI, not method). Datasette generally responds to HEAD and GET symmetrically for `.json` endpoints. But the `.db` endpoint serves binary content with a 403 in our config (`/sglawwatch.db` returned `403` live 2026-04-21 because databases aren't downloadable in the current `metadata.json` config) — HEAD vs GET both return 403.

**How to avoid:** Probe both HEAD and GET in the verifier for at least one canary URL. Use HEAD for checking only the status code (`-I`); use GET when checking body content (the fallthrough sniff).

**Warning signs:** Routing assertion passes for `curl -I` but fails for `curl`. Investigate by adding `-v` and checking which upstream Caddy proxied to.

### Pitfall 7: Frontend `/frontend-test` 404s post-flip because of routing-flip ordering bug

**What goes wrong:** You add a `path /frontend-test` to the `@datasette` matcher by mistake (e.g., copy-paste from a different test). Now `/frontend-test` routes to datasette → 404. You see "404 on /frontend-test" and conclude "frontend is broken" instead of "matcher is wrong."

**Why it happens:** Confusing the `@datasette` matcher (routes-to-datasette predicate) with the catch-all (routes-to-frontend default).

**How to avoid:** `verify_phase_03.sh` MUST include a positive frontend-reachability assertion: `curl -fsS http://localhost/frontend-test | grep -q '"status":"ok"'`. If it fails, the matcher is wrong (catching too much) — not the frontend.

**Warning signs:** Pre-flip Caddyfile worked, post-flip `/frontend-test` returns 404.

## Code Examples

### Example 1: The Phase-3 Caddyfile diff (full content)

The file BEFORE (current state, Phase 2 — verified by reading `Caddyfile` 2026-04-21):

```caddyfile
{
    auto_https off
    admin localhost:2019
}

:80 {
    reverse_proxy zeeker-datasette:8001

    # Phase-3 forward-compat sketch (DO NOT uncomment in Phase 2; ...)
    # @datasette_api {
    #     path *.json *.csv *.db /-/*
    # }
    # reverse_proxy @datasette_api zeeker-datasette:8001
    # reverse_proxy frontend:8000
}
```

The file AFTER (Phase 3):

```caddyfile
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

Header comment block at the top of the file should be updated from "Phase 2 ... transparent reverse proxy" to "Phase 3 ... suffix-based router" — see Pattern 1 above for the full file with updated comments.

[VERIFIED current Caddyfile content by `Read` 2026-04-21]

### Example 2: `scripts/verify_phase_03.sh` skeleton

Adapted from `scripts/verify_phase_02.sh` (which the planner can read for the surrounding bash scaffolding). Phase 3-specific check categories:

```bash
#!/usr/bin/env bash
# Phase 3 verifier — positive routing + negative routing + frontend reachability + parity.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ok()   { printf "  OK    %s\n" "$1"; }
fail() { printf "  FAIL  %s\n" "$1" >&2; FAILED=1; }
FAILED=0

echo "== Phase 3 verifier =="

# A. Caddyfile validates
echo
echo "A. Caddyfile validates"
if docker run --rm -v "$ROOT/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine \
   caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1; then
  ok "Caddyfile passes caddy validate"
else
  fail "Caddyfile invalid"
fi

# B. Stack is healthy
echo
echo "B. All three services healthy"
HEALTHS=$(docker compose ps --format json | jq -r '.Health // .State')
HEALTHY=$(echo "$HEALTHS" | grep -c '^healthy$' || true)
if [ "$HEALTHY" -eq 3 ]; then ok "3/3 healthy"; else fail "$HEALTHY/3 healthy"; fi

# C. POSITIVE ROUTING — these MUST reach datasette
echo
echo "C. Positive routing (must reach datasette)"

check_positive() {
    local path="$1" expected_substr="$2"
    local body
    body=$(curl -fsS "http://localhost${path}" 2>/dev/null || echo "__CURL_FAIL__")
    if echo "$body" | grep -q "$expected_substr"; then
        ok "$path → datasette ($expected_substr present)"
    else
        fail "$path missing expected '$expected_substr'"
    fi
}

check_positive "/-/versions.json" '"datasette"'
check_positive "/sglawwatch.json"  '"tables"'
check_positive "/sglawwatch/headlines.json?_size=1" '"rows"'

# .csv is plain-text; check status only
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch/headlines.csv?_size=1")
if [ "$HTTP" = "200" ]; then ok "/sglawwatch/headlines.csv?_size=1 → 200"; else fail ".csv got $HTTP"; fi

# .db is 403 in current config (databases not downloadable per metadata.json)
# but it MUST reach datasette (403 from datasette, NOT frontend's 404).
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch.db")
if [ "$HTTP" = "403" ] || [ "$HTTP" = "200" ]; then
    ok "/sglawwatch.db → datasette (HTTP $HTTP, not frontend-404)"
else
    fail ".db got $HTTP (expected 403 or 200 from datasette)"
fi

# /-/sql may be 404 (database-scoped) but MUST come from datasette HTML, not frontend
BODY=$(curl -s "http://localhost/-/sql")
if echo "$BODY" | grep -qi 'zeeker-base.css\|datasette'; then
    ok "/-/sql → datasette (zeeker-base.css/datasette in body)"
else
    fail "/-/sql did not reach datasette"
fi

# /-/search-all (cross-database search) — datasette plugin route
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/-/search")
if [ "$HTTP" = "200" ] || [ "$HTTP" = "404" ]; then
    # 200 if plugin exists; 404 if datasette returns its branded 404
    BODY=$(curl -s "http://localhost/-/search")
    if echo "$BODY" | grep -qi 'zeeker-base.css\|datasette\|search'; then
        ok "/-/search → datasette (HTTP $HTTP)"
    else
        fail "/-/search did not reach datasette (body lacks datasette markers)"
    fi
else
    fail "/-/search got $HTTP"
fi

# D. NEGATIVE ROUTING — these MUST reach frontend (= JSON 404)
echo
echo "D. Negative routing (HTML routes must return frontend 404, NOT datasette HTML)"

check_negative() {
    local path="$1"
    local body http
    http=$(curl -s -o /tmp/zeeker-neg-body -w '%{http_code}' "http://localhost${path}")
    body=$(cat /tmp/zeeker-neg-body)

    # The decisive fallthrough sniff: datasette HTML always references zeeker-base.css.
    # Frontend's 404 is `{"detail":"Not Found"}` JSON.
    if echo "$body" | grep -q 'zeeker-base.css'; then
        fail "$path FALLTHROUGH: datasette HTML served (zeeker-base.css present)"
        return
    fi

    # Frontend's default 404 has detail/Not Found
    if [ "$http" = "404" ] && echo "$body" | grep -q '"detail":"Not Found"'; then
        ok "$path → frontend 404 (correct)"
    else
        fail "$path got HTTP $http with body: $(echo "$body" | head -c 80)"
    fi
}

check_negative "/"
check_negative "/sglawwatch"
check_negative "/sglawwatch/headlines"
check_negative "/sg-gov-newsrooms"
check_negative "/zeeker-judgements"
check_negative "/developers"
check_negative "/about"
check_negative "/how-to-use"
check_negative "/status"
check_negative "/sources"

# E. FRONTEND REACHABILITY
echo
echo "E. Frontend /frontend-test still reachable"
BODY=$(curl -fsS "http://localhost/frontend-test")
if echo "$BODY" | grep -q '"status":"ok"' && echo "$BODY" | grep -q '"service":"zeeker-frontend"'; then
    ok "/frontend-test → frontend OK"
else
    fail "/frontend-test body unexpected: $BODY"
fi

# F. EDGE CASES
echo
echo "F. Edge cases"

# Multi-dot URL with query string
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/sg-gov-newsrooms/_zeeker_schemas.json?_size=10")
if [ "$HTTP" = "200" ]; then ok "multi-dot+query .json → 200"; else fail "multi-dot+query got $HTTP"; fi

# HEAD vs GET symmetry
HTTP_GET=$(curl -s  -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch.json?_size=1")
HTTP_HEAD=$(curl -sI -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch.json?_size=1")
if [ "$HTTP_GET" = "$HTTP_HEAD" ]; then ok "HEAD/GET symmetric ($HTTP_GET)"; else fail "HEAD=$HTTP_HEAD GET=$HTTP_GET"; fi

# Case-sensitivity (Caddy path matcher is case-INsensitive)
HTTP_LOWER=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/sglawwatch.json?_size=1")
HTTP_UPPER=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/SGLAWWATCH.JSON?_size=1")
# Both should reach datasette; datasette decides whether the upper-case database exists.
# What matters here is neither falls through to frontend.
BODY_UPPER=$(curl -s "http://localhost/SGLAWWATCH.JSON?_size=1")
if echo "$BODY_UPPER" | grep -q 'zeeker-base.css\|"error"\|"ok"'; then
    ok "uppercase .JSON also routes to datasette (HTTP $HTTP_UPPER)"
else
    fail "uppercase .JSON may have fallen through (body: $(echo "$BODY_UPPER" | head -c 80))"
fi

# CORS headers preserved (CLAUDE.md: all API endpoints have CORS enabled)
CORS=$(curl -sI "http://localhost/-/versions.json" | grep -i '^access-control-allow-origin:' || true)
if [ -n "$CORS" ]; then ok "CORS preserved: $CORS"; else fail "CORS header missing"; fi

# G. PARITY (REQ-api-byte-parity) — uses the parameterized verifier
echo
echo "G. API byte-parity vs .planning/baselines/phase-03-pre/"
export ZEEKER_BASELINE_DIR="$ROOT/.planning/baselines/phase-03-pre"
if bash scripts/verify_api_parity.sh; then
    ok "verify_api_parity.sh against phase-03-pre"
else
    fail "verify_api_parity.sh failed"
fi

echo
if [ "$FAILED" -eq 0 ]; then
    echo "Phase 3 verifier: ALL GREEN"; exit 0
else
    echo "Phase 3 verifier: FAILURES — see above"; exit 1
fi
```

**Notes for the planner:**
- The `check_negative` function is the most important code in this file. The `zeeker-base.css` body sniff is the decisive fallthrough guard — never remove it.
- The `.db` test accepts 403 OR 200 because the current `metadata.json` config blocks `.db` downloads (verified live: `/sglawwatch.db` returns 403). What matters for Phase 3 is that the response came from datasette (not from frontend's `{"detail":"Not Found"}`). The status code alone doesn't prove that; the absence of frontend's JSON shape does.
- The script exports `ZEEKER_BASELINE_DIR` before calling `verify_api_parity.sh`. This requires editing `verify_api_parity.sh` to honor that env var (one-line change — see Pitfall 3 fix recommendation).

### Example 3: `scripts/verify_api_parity.sh` parameterization (1-line edit)

Current (line 10):
```bash
BASELINE_DIR="$(git rev-parse --show-toplevel)/.planning/baselines/phase-02"
```

Changed to:
```bash
BASELINE_DIR="${ZEEKER_BASELINE_DIR:-$(git rev-parse --show-toplevel)/.planning/baselines/phase-03-pre}"
```

This makes the script respect a per-phase override (used by `verify_phase_03.sh`) while defaulting to the current phase's baselines if invoked standalone. **Default updated to `phase-03-pre`** because Phase 2's `phase-02/` directory was renamed (commit `ee3f3ad`) and no longer exists.

[VERIFIED hardcoded value via `Read` of scripts/verify_api_parity.sh line 10, 2026-04-21]

### Example 4: One-shot manual smoke check sequence

For a human running through the test plan interactively post-flip:

```bash
# 1. Validate Caddyfile
docker run --rm -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# 2. Reload Caddy
docker compose restart caddy

# 3. Wait for healthy
sleep 5; docker compose ps

# 4. Positive: datasette reachable
curl -fsS http://localhost/-/versions.json | jq -r .datasette.version    # → 0.65.2
curl -fsS http://localhost/sglawwatch.json | jq -r '.tables[0].name'     # → "headlines"
curl -fsS http://localhost/sglawwatch/headlines.json?_size=1 | jq -r '.rows | length'  # → 1

# 5. Negative: HTML routes 404 from frontend (not datasette)
curl -s http://localhost/sglawwatch | head -c 100
# Expected:  {"detail":"Not Found"}
# BUG signal: anything containing "<!DOCTYPE html>" or "zeeker-base.css"

# 6. Frontend reachability
curl -fsS http://localhost/frontend-test
# Expected: {"status":"ok","service":"zeeker-frontend"}

# 7. Run automated verifier
bash scripts/verify_phase_03.sh
```

[VERIFIED command shapes against live stack 2026-04-21 — all curl invocations were tested against the current Phase-2 stack and confirmed functional, except for the post-flip behavior which is the goal of Phase 3]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-handler reverse_proxy (Phase 2) | Named matcher + handler + catch-all (Phase 3) | This phase | First time we use Caddy as a router rather than a passthrough |
| Hardcoded baseline path in verifier | Env-var-parameterized `ZEEKER_BASELINE_DIR` | This phase | Future phases can re-baseline without editing scripts |
| Phase-2 `verify_phase_02.sh` (single-backend assertions) | Phase-3 `verify_phase_03.sh` (positive + negative routing + parity wrap) | This phase | Adds the negative-routing assertion category — verify Phase 2 didn't need |

**Deprecated/outdated within Phase 3 scope:** None. All Caddy syntax used here is current `caddy:2.11.2-alpine` (verified). The `path` matcher with suffix/prefix globs is how Caddy v2 has worked since v2.0.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `/static/css/zeeker-base.css` `<link>` reference appears in EVERY datasette-served HTML page (homepage, database, table, row, 404). | Pitfall 1, Example 2 (negative-routing sniff) | Verified live for `/`, `/sglawwatch`, and the `/frontend-test` 404 page. If a datasette HTML page exists that doesn't include `zeeker-base.css`, the negative-routing assertion would yield a false NEGATIVE (correctly routed but appears to be fallthrough). Mitigation: if discovered, expand the sniff to also check `data.zeeker.sg` (the title-bar text — appears in every datasette HTML). |
| A2 | FastAPI's default 404 response shape is `{"detail":"Not Found"}` with `Content-Type: application/json`. | Pitfall 1, Example 2 | [VERIFIED live 2026-04-21 — `docker compose exec frontend python -c ...` showed exactly this body.] If a future frontend version (FastAPI upgrade) changes the default 404 shape, the assertion needs updating. Low risk for Phase 3. |
| A3 | `caddy:2.11.2-alpine` `caddy validate` accepts the locked Caddyfile shape (named matcher with two `path` directives + two `reverse_proxy` lines). | Standard Stack, Pattern 3 | [VERIFIED matcher syntax via caddyserver.com/docs/caddyfile/matchers.] [VERIFIED `caddy validate` works for the analogous Phase-2 file via `02-03-SUMMARY.md`.] Validation should be re-run before commit; the cost is one Docker invocation. |
| A4 | `docker compose restart caddy` causes Caddy to re-read the bind-mounted Caddyfile (no inode-pinning issue when the container starts fresh). | Pattern 4 | [VERIFIED via Docker docs and community caddy.community/t/27308.] If the host filesystem itself has a stale view (highly unusual), `docker compose down caddy && docker compose up -d caddy` is the nuclear option. |
| A5 | The `verify_api_parity.sh` Phase-2 verifier produces meaningful diffs against `phase-03-pre` baselines for `*.json` URLs after the flip. | Architecture Patterns, REQ-api-byte-parity | The baselines were captured against the post-Caddy stack (per `phase-03-pre/README.md`). Phase 3 changes ONLY which Caddy directive routes `.json` traffic — the upstream is identical, the Host header is identical (same `localhost` entry), so byte-identical output is the expected behavior. Risk if wrong: surprise diffs in Category D (true topology-induced regression) — would need triage like Phase 2's. |
| A6 | The `path *.json` matcher fires for URLs like `/sg-gov-newsrooms/_zeeker_schemas.json?_size=10` (multi-dot path with query string). | Edge Cases | [VERIFIED via caddyserver.com/docs/caddyfile/matchers — "Path matches are exact but case-insensitive" and "*.suffix" is suffix match on the path component (query strings excluded).] The path component `/sg-gov-newsrooms/_zeeker_schemas.json` ends in `.json` — matches. Empirically verified live: this URL returns 200 against current Phase-2 stack. |
| A7 | Caddy auto-sorts `reverse_proxy @datasette ...` BEFORE `reverse_proxy frontend:8000` regardless of file order. | Architecture Patterns → Pattern 1, Anti-Patterns | [VERIFIED via caddyserver.com/docs/caddyfile/directives — "A directive with no matcher (matching all requests) is sorted last."] We still write matched-first for human readability and to match the PRD's snippet exactly. |
| A8 | `verify_api_parity.sh`'s `BASELINE_DIR` is the only hardcoded `phase-02` reference in the verifier scripts. | Don't Hand-Roll, Pitfall 3 | [VERIFIED via Grep `phase-02|phase-03` across `scripts/`.] Two hits: `scripts/verify_api_parity.sh` line 10 and `scripts/capture_baseline.sh` line 13. Phase 3 only needs to fix the parity script (capture isn't run in Phase 3); capture-script fix can ride along or be deferred. |
| A9 | `/-/sql` (without a database prefix) returns 404 from datasette (because Datasette's `/-/sql` is database-scoped: `/sglawwatch/-/sql`). | Example 2 | [VERIFIED live 2026-04-21 — `curl http://localhost/-/sql` returns 404 with datasette HTML body containing `zeeker-base.css`.] Phase 3 verifier must NOT require status 200 for `/-/sql`; it must require body to contain `zeeker-base.css`/`datasette` (proves it reached datasette). |

**The planner SHOULD verify A1 and A5 before locking task descriptions** — A1 is the basis of the negative-routing assertion; A5 is the basis of the parity reuse claim. Both are HIGH-confidence as researched, but the cost of being wrong is gate-failure noise.

## Open Questions

1. **Should Phase 3 also fix `scripts/capture_baseline.sh`'s hardcoded `phase-02` path, or defer to Phase 4?**
   - What we know: The script is not invoked during Phase 3. The hardcoded path is `OUT_DIR=...phase-02`.
   - What's unclear: Whether to bundle the fix here (clean atomic commit) or defer to Phase 4 (where it'll need updating to `phase-04-pre` anyway).
   - Recommendation: Bundle a parameterized fix (env-var with `phase-03-pre` default) along with the parity-script fix. Same diff shape; same commit; less drift. The planner should explicitly include this as a sub-task or explicitly defer it.

2. **Should `verify_phase_03.sh` also run `verify_phase_02.sh` for completeness, or is it strictly additive?**
   - What we know: `verify_phase_02.sh` checks topology invariants that Phase 3 inherits (datasette has no `ports:`, frontend has no sqlite3, only caddy publishes ports, healthchecks). These are still true in Phase 3.
   - What's unclear: Whether Phase 3 wants the entire Phase-2 suite included or just the routing-specific deltas.
   - Recommendation: `verify_phase_03.sh` should INCLUDE the topology checks from Phase 2 by either (a) sourcing/calling `verify_phase_02.sh` as a sub-step, or (b) duplicating the small handful of essential checks. Recommend (a) — invoke `verify_phase_02.sh` as the first big check, then layer routing-specific checks on top. This way Phase 3 inherits the full topology gate AND adds the routing gate.

3. **Should the phase add a `403 -> 404` redirect for `.db` to make the user-facing experience better?**
   - What we know: `/sglawwatch.db` returns 403 from datasette (databases not downloadable per `metadata.json` config). After Phase 3, this still routes to datasette (because `*.db` matches) and still returns 403.
   - What's unclear: Whether this is desired behavior or should be reshaped.
   - Recommendation: OUT OF SCOPE for Phase 3. The routing contract is "`.db` → datasette." What datasette does with the request is a separate concern (and it might be fixed in a Phase-7 datasette-shrink config update, or not at all — the user can choose to allow downloads in `metadata.json` later). Leave as-is.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Reload caddy + run `caddy validate` one-shot | ✓ | (Phase 2 verified) | — |
| Docker Compose | `docker compose restart caddy`, exec | ✓ | v5.1.0 (Phase 2 verified) | — |
| `caddy:2.11.2-alpine` image | Already pulled | ✓ | 2.11.2 | — |
| `curl` (host) | Verifier script live probes | ✓ | 8.7.1 (Phase 2 verified) | — |
| `jq` (host) | Parsing JSON responses in verifier | ✓ | 1.7.1 (Phase 2 verified) | — |
| `bash` | Verifier scripts | ✓ | (default macOS/Linux) | — |
| `git` (host) | `git rev-parse --show-toplevel` in scripts | ✓ | (Phase 2 verified) | — |
| Three-service compose stack RUNNING | All verification | ✓ | Currently up (verified `docker compose ps` 2026-04-21T07:00Z: 3/3 healthy, 4 hours uptime) | — |

**Missing dependencies with no fallback:** None. Everything Phase 3 needs is already on the dev box and proven working in Phase 2.

**Missing dependencies with fallback:** None.

**Live state at research time:** Compose stack is up (caddy + datasette + frontend, all healthy, 4 hours uptime). Verified by `docker compose ps` at 2026-04-21T07:00Z.

## Validation Architecture

> Section included because `.planning/config.json` does not exist; per the agent rules, absence of `workflow.nyquist_validation` defaults to **enabled**.

### Test Framework

| Property | Value |
|----------|-------|
| Test type | Bash assertion script (no unit-test framework — Phase 3 is infrastructure config, not application code) |
| Quick run command | `docker run --rm -v "$(pwd)/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` (~3s; static check only, no stack interaction) |
| Full suite command | `bash scripts/verify_phase_03.sh` (full bring-up assertions; 30-90s) |
| Phase-2 verifier (still relevant; topology unchanged) | `bash scripts/verify_phase_02.sh` — should be invoked from `verify_phase_03.sh` as a prerequisite step |
| Frontend Python tests (smoke) | `cd packages/zeeker-frontend && uv run pytest -q` (~2s; unchanged from Phase 2) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-suffix-routing-contract | `*.json` routes to datasette | smoke | `curl -fsS http://localhost/sglawwatch.json \| jq -e '.tables \| length > 0'` | ❌ Wave 0 (in `verify_phase_03.sh`) |
| REQ-suffix-routing-contract | `*.csv` routes to datasette | smoke | `[ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost/sglawwatch/headlines.csv?_size=1)" = "200" ]` | ❌ Wave 0 |
| REQ-suffix-routing-contract | `*.db` routes to datasette (status 200 OR 403; either proves datasette responded) | smoke | `code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost/sglawwatch.db); [ "$code" = "200" ] \|\| [ "$code" = "403" ]` | ❌ Wave 0 |
| REQ-suffix-routing-contract | `/-/*` routes to datasette | smoke | `curl -fsS http://localhost/-/versions.json \| jq -e '.datasette'` | ❌ Wave 0 |
| REQ-suffix-routing-contract | HTML routes (`/`, `/{db}`, `/{db}/{table}`, etc.) route to frontend (= JSON 404), NOT datasette HTML | smoke (the load-bearing test) | `body=$(curl -s http://localhost/sglawwatch); echo "$body" \| grep -q 'zeeker-base.css' && exit 1; echo "$body" \| grep -q '"detail":"Not Found"'` | ❌ Wave 0 |
| REQ-suffix-routing-contract | `/frontend-test` routes to frontend (proves frontend reachability) | smoke | `curl -fsS http://localhost/frontend-test \| jq -e '.status == "ok"'` | ❌ Wave 0 |
| REQ-api-byte-parity | `*.json` URLs return identical bytes pre/post (modulo timestamps + version strings) | regression | `ZEEKER_BASELINE_DIR=$ROOT/.planning/baselines/phase-03-pre bash scripts/verify_api_parity.sh` | ❌ Wave 0 (script edit needed: parameterize `BASELINE_DIR`) |
| REQ-incremental-migration | Single-file commit; `git revert <hash> && docker compose restart caddy` returns to Phase 2 | manual / structural | `git show <hash> --stat` shows only `Caddyfile` modified (and the new verifier + plan docs in separate commits) | manual review |
| Internal: Caddyfile validates | `caddy validate` passes | static | `docker run --rm -v "$ROOT/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile` | ❌ Wave 0 |
| Internal: All three services healthy after reload | Caddy can reload without breaking the dependency graph | runtime | `docker compose ps --format json \| jq -r '.Health' \| grep -c '^healthy$'` returns `3` | ❌ Wave 0 (covered by reusing Phase-2 check 7) |
| Internal: CORS headers preserved | `--cors` from datasette flows through Caddy | runtime | `curl -sI http://localhost/-/versions.json \| grep -i '^access-control-allow-origin: \*'` | ❌ Wave 0 |
| Internal: Multi-dot URL with query string still matches | `/sg-gov-newsrooms/_zeeker_schemas.json?_size=10` returns 200 | smoke | `[ "$(curl -s -o /dev/null -w '%{http_code}' 'http://localhost/sg-gov-newsrooms/_zeeker_schemas.json?_size=10')" = "200" ]` | ❌ Wave 0 (edge-case section of `verify_phase_03.sh`) |
| Internal: HEAD/GET symmetric | Caddy matcher fires the same on HEAD as GET | smoke | compare `%{http_code}` of `curl -s -o /dev/null` vs `curl -sI -o /dev/null` for one canary | ❌ Wave 0 |

### Sampling Rate

- **Per task commit** (Caddyfile edit): `caddy validate` (~3s) — fast feedback that syntax isn't broken.
- **Per wave merge** (Caddyfile + verifier + test plan complete): full `bash scripts/verify_phase_03.sh` (~30-90s) — full positive + negative + parity + edge-case suite.
- **Phase gate**: All-green `verify_phase_03.sh` exit 0, then human review of `03-TEST-PLAN.md` for completeness, then `/gsd-verify-work`.

### Wave 0 Gaps

The following test infrastructure does NOT exist yet and must be created before Phase 3 can claim "done":

- [ ] `scripts/verify_phase_03.sh` — NEW; ~120 lines of bash. Structure: positive routing → negative routing (with body-content fallthrough guards) → frontend reachability → edge cases (multi-dot, HEAD/GET, case-insensitivity, CORS) → parity wrap. Skeleton in Code Examples → Example 2.
- [ ] `scripts/verify_api_parity.sh` — EDITED; one-line change to parameterize `BASELINE_DIR` via env var with `phase-03-pre` default. Diff in Code Examples → Example 3.
- [ ] `scripts/capture_baseline.sh` — OPTIONAL EDIT; same parameterization treatment for the `OUT_DIR` (line 13). Phase 3 doesn't run capture, but bundling the fix avoids drift. (See Open Questions #1.)
- [ ] `.planning/phases/03-flip-suffix-based-routing/03-TEST-PLAN.md` — NEW per CONTEXT; outline given in Specifics section of CONTEXT.md.
- [ ] `Caddyfile` — EDITED (3-line body → 4-line block + comment update). Diff in Code Examples → Example 1.

## Sources

### Primary (HIGH confidence)

- [Caddy: Request matchers (Caddyfile)](https://caddyserver.com/docs/caddyfile/matchers) — fetched 2026-04-21. Verified: `*.suffix` is suffix match; multiple paths in one directive are OR'd; multiple `path` directives in one named matcher are also OR'd; case-insensitive; query-string-agnostic; URL-decoded normalization; multi-slash merging.
- [Caddy: reverse_proxy directive](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) — fetched 2026-04-21. Verified: standard `reverse_proxy [matcher] upstream` form; default Host header preservation.
- [Caddy: Caddyfile directives sorting](https://caddyserver.com/docs/caddyfile/directives) — fetched 2026-04-21. Verified: "A directive with no matcher (matching all requests) is sorted last." Catch-all auto-sorted regardless of file order.
- [Caddy: Command line](https://caddyserver.com/docs/command-line) — fetched 2026-04-21. Verified: `caddy reload --config <path> --adapter caddyfile` is "the correct, semantic way to change/reload"; admin endpoint required; `caddy validate` does provisioning-level check (stronger than syntax).
- Local repo inspection (Caddyfile, docker-compose.yml, scripts/verify_phase_02.sh, scripts/verify_api_parity.sh, scripts/capture_baseline.sh, packages/zeeker-frontend/src/zeeker_frontend/main.py, .planning/baselines/phase-03-pre/) — direct read 2026-04-21.
- Live stack probes 2026-04-21T07:00Z — `docker compose ps` (3/3 healthy), `curl -I http://localhost/sglawwatch.db` (HTTP 403, `Server: uvicorn`), `curl http://localhost/sglawwatch | head -c 100` (datasette HTML with `zeeker-base.css` reference), `docker compose exec frontend python -c ...` (FastAPI default 404 = `{"detail":"Not Found"}` JSON).
- `.planning/baselines/phase-03-pre/README.md` — confirms baselines were captured 2026-04-21 against post-Phase-2 stack with datasette 0.65.2 and three databases.

### Secondary (MEDIUM confidence)

- [Caddy Docker community: bind-mount inode swap (issue #364)](https://github.com/caddyserver/caddy-docker/issues/364) — surfaced via WebSearch 2026-04-21; informs Pitfall 2.
- [caddy.community t/27308 — Compose recipes](https://caddy.community/t/getting-caddy-to-work-with-docker-compose/27308) — surfaced via WebSearch; informs Pattern 4.
- [DEV.to: Routing multiple paths to a reverse proxy using Caddy](https://dev.to/tylerlwsmith/routing-multiple-paths-to-a-reverse-proxy-19on) — corroborates the named-matcher pattern used here.
- `.planning/phases/02-dual-service-bring-up/02-RESEARCH.md` Pattern 2 — Phase-3 forward-compat sketch; deliberately written for this phase's reference.
- `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` — parity triage methodology (Categories A/B/C/D); Phase 3 inherits this framework.
- `.planning/phases/02-dual-service-bring-up/02-03-SUMMARY.md` — Phase-2 plan that authored the Caddyfile + ran `caddy validate` against `caddy:2.11.2-alpine`; confirms validation pattern works.

### Tertiary (LOW confidence — none used as load-bearing claims)

None. Every routing-correctness claim in this research traces to either an official docs URL (HIGH) or an empirical live probe (HIGH).

## Metadata

**Confidence breakdown:**

- Caddyfile syntax (`path` matcher semantics, named matcher OR rules, directive sorting): **HIGH** — every claim cross-referenced against caddyserver.com/docs/caddyfile/{matchers,directives,directives/reverse_proxy} fetched 2026-04-21.
- Caddy reload mechanics (`docker compose restart caddy` vs `caddy reload`, bind-mount inode gotcha): **HIGH** — official docs + corroborating GitHub issue + community thread.
- Negative-routing assertion design (body-content sniff for `zeeker-base.css`): **HIGH** — empirically verified against live Phase-2 stack 2026-04-21; FastAPI default 404 shape verified by direct probe.
- Edge cases (multi-dot URL, HEAD/GET symmetry, case-insensitivity): **HIGH** — Caddy docs explicit; empirically verified against live stack for the multi-dot case.
- `verify_api_parity.sh` reuse strategy (parameterize `BASELINE_DIR`): **HIGH** — Phase-3 baselines exist (verified by directory listing); script edit is mechanical.
- Production-overlay compatibility of the `:80` site block: **MEDIUM** — Caddy supports multiple site blocks keyed by hostname AND port-only addresses simultaneously, so adding a `data.zeeker.sg { ... }` block in a future overlay won't conflict with the `:80` block. Verified conceptually against Caddyfile docs but not empirically tested (overlay doesn't exist yet).

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 for Caddy version pin (re-verify if `caddy:2.11.2-alpine` is rolled forward); 2026-10-21 for matcher semantics (Caddy v2 path matcher API has been stable since 2.0).

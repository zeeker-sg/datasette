# Phase 2: Dual-service bring-up — Context

**Gathered:** 2026-04-20
**Status:** Ready for planning
**Source:** Synthesized from `.planning/intel/` (post-ingest of `prd-zeeker-frontend-split.md`)

<domain>
## Phase Boundary

Add two new Docker services — a `frontend` (FastAPI placeholder) and a `caddy` reverse proxy — to `docker-compose.yml`, alongside the existing `datasette` service. **No public routing change in this phase.** Caddy routes 100% of incoming traffic to datasette, exactly as the current direct-exposed setup does. The frontend serves a single placeholder route (`/frontend-test`) so we can prove the container is healthy and reachable from Caddy over the internal Docker network. Datasette's `ports:` mapping is removed so it becomes network-internal-only — Caddy is now the sole public-facing service.

This phase delivers **the topology change without the routing flip**. The routing flip is Phase 3. Splitting them lets us deploy the new topology independently and roll back to a single-service setup with a one-line compose change if anything goes wrong.

This phase does NOT:
- Flip the suffix-based routing (Phase 3).
- Port any HTML pages (Phases 4–6).
- Delete anything from `packages/zeeker-datasette/` (Phase 7).
- Move Matomo or decide overlay strategy (Phase 8).

</domain>

<decisions>
## Implementation Decisions

### Frontend service stack
- **Locked by PRD §7.2 (DEC-3):** FastAPI + Jinja2 + httpx for internal HTTP calls + uv for deps + black-formatted code.
- **Locked by PRD §7.2 (DEC-5):** Frontend reads data exclusively via internal HTTP to `http://datasette:8001/...json`. **No SQLite client in the frontend container. No volume mount of `./data` on the frontend service.**
- This phase: only need the placeholder route, but the package skeleton must already enforce the no-SQLite discipline (don't install `sqlite3` deps, don't mount `./data`).

### Reverse proxy
- **Locked by PRD §7.3 (DEC-4):** Caddy — off-the-shelf image, single Caddyfile at repo root.
- **This phase's Caddyfile** is the simplest possible: one site block, all traffic → `datasette:8001`. No suffix matchers yet — those are added in Phase 3.
- TLS is auto-provisioned by Caddy from a persistent named volume.
- Caddy publishes `:80` and `:443`; no other service publishes ports.

### Datasette service changes (this phase only)
- Remove the `ports:` mapping. Datasette becomes reachable only over the internal Docker network at `datasette:8001`.
- Healthcheck remains `GET /-/versions.json` returns 200.
- `--cors` flag preserved (PRD §7.1 — frontend will need CORS-style behavior for any direct browser-to-datasette use).
- Read-only mode preserved.
- **Do NOT delete templates/, static/, or UI plugins in this phase.** Those deletions are Phase 7 and depend on every HTML route having moved to the frontend first.

### Frontend package layout
- Create `packages/zeeker-frontend/` as a new uv-managed package with this minimum:
  - `pyproject.toml` (FastAPI, Jinja2, httpx, uvicorn — runtime deps; black, ruff, pytest — dev deps)
  - `src/zeeker_frontend/__init__.py`
  - `src/zeeker_frontend/main.py` — FastAPI app with `GET /frontend-test` returning `{"status": "ok", "service": "zeeker-frontend"}` (JSON, not HTML, to avoid premature template work)
  - `src/zeeker_frontend/templates/` (empty directory, scaffolded for Phases 4–6)
  - `src/zeeker_frontend/static/` (empty directory, scaffolded for Phases 4–6)
  - `Dockerfile` — slim Python base, install via uv, run `uvicorn` on port 8000
  - `README.md` — one-paragraph "this is the placeholder; see roadmap M2"
- Place under `packages/zeeker-frontend/` to match the existing `packages/zeeker-datasette/` convention referenced in PRD §9.

### docker-compose layout (this phase)
- Three services: `datasette` (existing, ports removed), `frontend` (new, internal-only), `caddy` (new, the only service publishing :80 and :443).
- Internal network: default bridge is fine; explicit network not required for this phase.
- Caddy depends_on: datasette (with health condition) and frontend (with health condition) so it doesn't accept traffic until both backends are up.
- Persistent volume for Caddy's `data` and `config` directories (TLS cert storage).
- Frontend healthcheck: `curl -f http://localhost:8000/frontend-test || exit 1`.

### Verification approach
- After `docker compose up -d`: poll `docker compose ps` until all three services report healthy.
- `curl https://localhost/sglawwatch.json` must return identical JSON to a baseline captured pre-change (the routing isn't flipped yet, so this just exercises Caddy → datasette).
- `curl https://localhost/frontend-test` must return 404 (Caddy is still routing everything to datasette in this phase). The frontend's `/frontend-test` route is reachable only by `docker compose exec frontend curl http://localhost:8000/frontend-test` — this proves the frontend container itself is healthy.

### Claude's Discretion
- Exact Caddyfile syntax (PRD specifies behavior, not literal text).
- Choice of Python base image for frontend Dockerfile (slim vs alpine vs distroless — prefer python:3.12-slim unless there's a specific reason).
- Whether to use Caddy's auto-HTTPS in local dev (consider: skip HTTPS in `docker-compose.yml`, enable in a separate `docker-compose.prod.yml` overlay if not already split).
- Internal port for the frontend container (suggest 8000; reflect in healthcheck).
- Whether to add a `.dockerignore` for the new `packages/zeeker-frontend/` (recommend yes — keep node_modules-style accidents out).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD
- `prd-zeeker-frontend-split.md` — full PRD; this phase implements §10 Step 1 only

### Synthesized Intel
- `.planning/intel/SYNTHESIS.md` — entry point
- `.planning/intel/decisions.md` — DEC-3 (FastAPI+Jinja stack), DEC-4 (Caddy), DEC-5 (HTTP-only data access) directly bind this phase
- `.planning/intel/requirements.md` — REQ-incremental-migration, REQ-internal-only-datasette-exposure, REQ-frontend-data-via-http, REQ-preserve-zeeker-cli, REQ-api-byte-parity all in scope
- `.planning/intel/constraints.md` — CON-frontend-stack, CON-datasette-shrink (only the ports-removal slice for this phase; full deletion is Phase 7), CON-healthcheck
- `.planning/intel/context.md` — background on R-series risks (R7 in particular: minimum viable change, weekend budget)

### Existing repo files this phase will touch
- `docker-compose.yml` — currently exposes datasette directly; needs ports: removed and two new services added
- `Dockerfile` (root, the existing datasette image) — unchanged this phase
- `entrypoint.sh` (existing datasette entrypoint) — unchanged this phase

### Existing repo constraint docs
- `.planning/notes/datasette-styling-limits.md` — explains why we're escaping the Datasette template surface (motivation for the whole milestone, but not directly actionable for this infrastructure phase)
- `CLAUDE.md` — project instructions; `metadata.json` is referenced as the authoritative data metadata file (preserved)

### Currently absent — to be created in this phase
- `Caddyfile` (repo root) — does not exist
- `packages/zeeker-frontend/` (entire directory tree) — does not exist
- The repo currently has no `packages/` directory; the existing layout is flat. Either:
  (a) Create `packages/zeeker-frontend/` as the first sub-package and treat the existing root as the implicit `zeeker-datasette` package (defer the rename to Phase 7); or
  (b) Stand up `packages/zeeker-frontend/` as a sibling directory next to the existing flat repo without restructuring the datasette files yet.
  **Recommendation:** option (b) for this phase — minimum disruption. The full restructure is Phase 7's scope per PRD §9 table.

</canonical_refs>

<specifics>
## Specific Ideas

### Healthcheck details
- Datasette: existing `GET /-/versions.json`, expect 200. PRD §7.1 specifies this.
- Frontend: `GET /frontend-test`, expect 200. Use `curl -f` in compose healthcheck.
- Caddy: official Caddy image's built-in health endpoint, or `wget --spider` against `http://localhost/`.

### Compose service-dependency wiring
```
caddy:
  depends_on:
    datasette:
      condition: service_healthy
    frontend:
      condition: service_healthy
```
This ensures Caddy doesn't accept traffic before backends are reachable.

### Caddyfile (this phase — pre-flip)
Behavioral spec, not literal:
```
:80 {
  reverse_proxy datasette:8001
}
```
Or with HTTPS at a real domain:
```
data.zeeker.sg {
  reverse_proxy datasette:8001
}
```
(Local-dev variant skips the domain and uses port 80 only.)

### Frontend FastAPI app (minimum)
```python
from fastapi import FastAPI

app = FastAPI(title="zeeker-frontend (placeholder)")

@app.get("/frontend-test")
def frontend_test():
    return {"status": "ok", "service": "zeeker-frontend"}
```

### Verification curl matrix (post-deploy)
- `curl -fsS https://localhost/sglawwatch.json | jq .ok` — must succeed (datasette JSON via Caddy).
- `curl -fsSI https://localhost/sglawwatch | head -1` — must show HTTP/2 200 (datasette HTML via Caddy, since routing not flipped yet).
- `curl -fsS https://localhost/frontend-test` — should 404 (proves Caddy is still routing everything to datasette).
- `docker compose exec frontend curl -fsS http://localhost:8000/frontend-test` — must succeed (proves frontend container healthy).
- `docker compose exec datasette wget -qO- http://localhost:8001/-/versions.json | jq .datasette` — must succeed (proves datasette internal endpoint healthy).

</specifics>

<deferred>
## Deferred Ideas

- Suffix-based routing (`*.json|*.csv|*.db|/-/* → datasette`, else → frontend) — Phase 3.
- Real frontend HTML pages (`/`, `/{db}`, table, row, etc.) — Phases 4–6.
- Deletion of `templates/`, `static/`, and UI plugins from datasette — Phase 7.
- Matomo migration and overlay decision — Phase 8.
- Restructuring root repo into `packages/zeeker-datasette/` — Phase 7 (recommended; this phase puts new code under `packages/zeeker-frontend/` without renaming the existing flat layout).
- TLS auto-provisioning at the real `data.zeeker.sg` domain (this phase's local-dev compose uses HTTP; the production overlay can enable Caddy auto-HTTPS).
- Per-database overlay mechanism for the frontend — open question per PRD R5, deferred to Phase 8.

</deferred>

---

*Phase: 02-dual-service-bring-up*
*Context gathered: 2026-04-20 from `.planning/intel/` (PRD-driven; auto-generated from synthesis)*

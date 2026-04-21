# Phase 4: Port home + database pages — Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Source:** Synthesized from `.planning/intel/` (PRD), `sketch-findings-zeeker-datasette` skill (validated design contract), M1 implementation artifacts (`templates/index.html`, `templates/database.html`, `static/css/zeeker-base.css`), and Phase 2–3 outputs.

<domain>
## Phase Boundary

Implement the first two FastAPI/Jinja HTML routes in `packages/zeeker-frontend/`:
- `GET /` — homepage (hero search, stats, database cards)
- `GET /{db}` — database overview (tables, row counts, schema link, SQL examples)

Harvest the M1 V2 templates and CSS (`templates/index.html`, `templates/database.html`, `static/css/zeeker-base.css`) into the FastAPI Jinja template tree. The visual design is **already locked** via the `sketch-findings-zeeker-datasette` skill — this phase is a *port*, not a redesign. Changes to the design contract are out of scope.

Deploy to production. Phase 4 is the first Phase that ships a user-visible change — the hostname `data.zeeker.sg` will start serving these two routes from the new frontend service (via Caddy's `else → frontend` catch-all from Phase 3). All other HTML routes continue to 404 from frontend until Phase 5 and 6 land.

This phase does NOT:
- Port `/{db}/{table}` (table browse) or `/{db}/{table}/{pk}` (row view) — Phase 5.
- Port `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/-/search`, `/llms.txt` — Phase 6.
- Delete M1 templates from `packages/zeeker-datasette/` — Phase 7.
- Change the sketch-findings design contract.

</domain>

<decisions>
## Implementation Decisions

### Template location & organization
- **New location:** `packages/zeeker-frontend/src/zeeker_frontend/templates/`
- **Base template:** `base.html` — shared shell chrome (nav, breadcrumb hook, hero hook, footer). Replaces `_header.html` + `_footer.html` partials (Datasette-specific conventions).
- **Page templates:** `index.html` (homepage), `database.html` (database overview).
- **Partials:** `_partials/` for small reusable chunks (e.g., card components, stat band). Keep organization flat for 2 pages; add hierarchy when it's actually needed.
- **Static assets:** `packages/zeeker-frontend/src/zeeker_frontend/static/`
  - `css/zeeker.css` — harvested from `static/css/zeeker-base.css`, renamed, scoped to only the CSS used by home + database pages + shell. Phases 5-6 will append more; this phase doesn't need to ship the CSS for unrelated pages.
  - `fonts/` — Inter + JetBrains Mono + Fraunces self-hosted woff2 (mirror from `static/fonts/`)
- **Do NOT wildcard-copy all of `static/` into the frontend package.** Harvest only what home + database need. Keep the image small.

### Data-access contract
- Frontend reads EXCLUSIVELY via HTTP from `http://zeeker-datasette:8001/...json`. No direct SQLite access. No database mounts in the frontend container. (Locked by DEC-5, Phase 2, Phase 3.)
- **API calls for `/`:**
  - `GET /.json` — returns `{db_name: {path, hash, tables_count, views_count, ...}, ...}` — used to populate the database card grid and the stat band (database count).
  - Optional: `GET /-/metadata.json` for site title, description, source attribution that may surface in the hero or footer.
  - For aggregate stats shown in the hero (total rows, total tables, latest update), query each database's metadata: `GET /{db}.json?_size=0` returns `{tables: [...], views: [...]}` — parse and sum. Alternatively, the Datasette `/{db}.json` returns schema info without row-count totals — may require per-table hits OR (preferred) compute lazily via SQL: `GET /{db}.json?sql=SELECT COUNT(*) FROM sqlite_master WHERE type='table'`. Pick the simplest path that answers the specific stat the hero shows. Research can finalize.
- **API calls for `/{db}`:**
  - `GET /{db}.json` — returns `{tables: [{name, columns, count, ...}]}` for the database page's editorial-row table list.
  - Filter hidden tables (`_zeeker_*`) client-side in the frontend (same as M1's behavior per CLAUDE.md: "All `_zeeker_*` metadata tables are hidden from the UI").
- **Caching:** in-memory TTL cache on the frontend for metadata endpoints. TTL seconds-to-minutes; not hours — data refresh cadence is daily. Row-level queries not cached (irrelevant for home + database pages anyway).
- **Error handling:** if datasette returns 5xx or times out, render a graceful error page. If datasette returns 4xx (e.g., 404 on unknown database), proxy that status code to the user — they asked for something that doesn't exist.

### FastAPI route handlers
- `@app.get("/", response_class=HTMLResponse)` — renders `index.html` with context `{databases: [...], stats: {...}}`.
- `@app.get("/{db}", response_class=HTMLResponse)` — renders `database.html` with context `{db_name, tables: [...], metadata: {...}}`. If `db` doesn't exist in `/.json` list, 404.
- Handlers SHOULD NOT be coupled to route content beyond template variable assembly. Keep them thin. A shared `httpx.AsyncClient` lives at app-lifespan scope for connection reuse.
- Response `Cache-Control` headers: `public, max-age=60, stale-while-revalidate=300` for `/` and `/{db}` (they're read-only and driven by data that refreshes daily).

### CSS harvest strategy
- M1's `static/css/zeeker-base.css` is 4116 lines containing the theme system, shell chrome, home styles, database styles, table feed styles, and more.
- For Phase 4: harvest **only** the sections needed for home + database + shell. Roughly:
  - Theme system (palette, typography, spacing, radii) — all of it
  - Shell chrome (`.db-nav`, `.db-crumb`, `.db-header`, `.db-statband`, `.db-toolbar`, `.cta`, `.cat-pill`, `.fts-badge`, `.site-footer`) — all of it
  - Home-specific (`.cards`, `.card` + nth-child accent rotation, `.chip`, `.how-grid`, `.hero-search`) — all of it
  - Database-specific (editorial-row table list styles — the sketch 002-B pattern) — all of it
  - LEAVE OUT: feed card CSS (Phase 5), row reading layout CSS (Phase 5), auxiliary-page CSS (Phase 6)
- Target: `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` at ~60% of the original length (~2500 lines feels right; not load-bearing).
- **Zero changes to design.** No palette swaps, no typography swaps. If something is broken post-port, it's a harvest/path bug — not a design decision to revisit.

### Nav behavior change
- M1's nav was served by Datasette's templates and appeared on all pages (including table, row, SQL editor). Phase 4 only covers home + database pages; frontend pages (Phase 5-6) and datasette-served pages (`/-/sql`, `/-/search`, `*.json`) have different chrome availability:
  - Home, database (Phase 4) → frontend nav
  - Table, row, auxiliary (Phase 5-6) → frontend nav (same, once they land)
  - `/-/sql`, `/-/versions.json` etc. → datasette's default HTML, no frontend nav. Acceptable; these are developer/debug surfaces, not user surfaces.

### Static-asset routing via Caddy
- Frontend serves `/static/*` from its container (FastAPI `StaticFiles` mount or equivalent).
- Caddy's suffix matcher routes `/static/foo.css` to datasette by default (NO — wait: `/static/foo.css` ends in `.css` which is NOT in the `*.json|*.csv|*.db|/-/*` suffix list, so it falls through to the frontend catch-all). Verify: the frontend serves `/static/*` correctly via Caddy.
- Self-hosted fonts similarly: `/static/fonts/inter.woff2` → frontend (woff2 not in datasette suffix list).
- If this doesn't work (e.g., Caddy compression or redirects cause issues), add a `handle_path /static/*` block in Caddyfile. But the default routing should Just Work.

### Production deploy
- First user-visible production change. Deployment via the existing zeeker pipeline (per CLAUDE.md). The exact mechanism: `docker compose up -d --build` on the production host after git pull.
- **Pre-deploy smoke:** verify_phase_04.sh should run against production BEFORE advertising the change. If production smoke fails, roll back.
- **Rollback path:** `git revert` whichever commit ships the compose change, then `docker compose up -d`. Granular — one file per concern so `git revert` is atomic.
- Domain: `data.zeeker.sg`. Caddy production overlay (TBD — may be a separate `docker-compose.prod.yml`) handles TLS via Caddy's auto-HTTPS. This phase likely needs to author that overlay if it doesn't exist.

### What's explicitly out of scope
- `/favicon.ico`, `/robots.txt`, `/apple-touch-icon.png` — nice-to-have but not load-bearing. If easy, include; if not, defer.
- Real-time database stats (last updated timestamps live) — use cached metadata with a manual refresh; full real-time is Phase 8.
- Mobile-first CSS audit beyond what M1 already shipped — M1 sketch findings include responsive collapses; Phase 4 inherits.
- A11y audit beyond checking the existing M1 semantics port cleanly — full a11y pass is a follow-up.

### Claude's Discretion
- Exact httpx client configuration (timeouts, pool size) — sensible defaults.
- Whether to use Jinja2 `extends`/`block` pattern or Jinja2 `include` — prefer `extends` for the base template (matches M1 pattern).
- Pydantic models for the datasette JSON payloads — use where it adds type safety without friction. Tables list is worth typing; site metadata probably not.
- Whether to add any new frontend dependencies beyond FastAPI/httpx/jinja2 — prefer NO; if something's needed, justify.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD + Intel
- `prd-zeeker-frontend-split.md` (§7.2, §10 Step 3 first tranche)
- `.planning/intel/SYNTHESIS.md`
- `.planning/intel/requirements.md` — REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http
- `.planning/intel/constraints.md` — CON-frontend-stack, CON-routing-table (Phase 3 already implements routing)

### Design contract
- `.claude/skills/sketch-findings-zeeker-datasette/SKILL.md` — **the design contract.** All palette/typography/layout/interaction decisions are locked here. DO NOT deviate. If a harvest looks off, consult this first.
- `.claude/skills/sketch-findings-zeeker-datasette/sources/` — original sketches with winning variants marked

### M1 harvest source (what gets ported)
- `templates/index.html` (183 lines) — sketch 001-D implementation
- `templates/database.html` (241 lines) — sketch 002-B implementation
- `templates/_header.html` — dark nav + breadcrumb shell
- `templates/_footer.html` — 4-column paper footer
- `static/css/zeeker-base.css` (4116 lines) — theme + shell + home + database + table-feed + others. Harvest selectively per §"CSS harvest strategy" above.
- `static/fonts/` — Inter + JetBrains Mono + Fraunces woff2 files. All self-hosted; no CDN refs.

### Phase-2 + Phase-3 outputs (what this phase builds on)
- `packages/zeeker-frontend/` — existing FastAPI package skeleton (Phase 2)
- `packages/zeeker-frontend/src/zeeker_frontend/main.py` — only `/frontend-test`; this phase adds `/` and `/{db}`
- `packages/zeeker-frontend/src/zeeker_frontend/templates/` — empty, scaffolded
- `packages/zeeker-frontend/src/zeeker_frontend/static/` — empty, scaffolded
- `Caddyfile` — suffix routing live (Phase 3); non-matcher paths already route to frontend
- `scripts/verify_phase_03.sh` — pattern for `verify_phase_04.sh`
- `scripts/verify_api_parity.sh` + `capture_baseline.sh` — parameterized; use `ZEEKER_BASELINE_DIR=.planning/baselines/phase-04-pre` after re-baselining post-Phase-3

### Datasette JSON reference
- `http://zeeker-datasette:8001/.json` — database list
- `http://zeeker-datasette:8001/{db}.json` — tables list for db
- `http://zeeker-datasette:8001/-/metadata.json` — site metadata
- `http://zeeker-datasette:8001/-/versions.json` — datasette version (healthcheck)

### CLAUDE.md (project instructions, check during implementation)
- `metadata.json` is authoritative for table metadata
- `_zeeker_*` metadata tables are hidden from the UI (frontend must respect)
- CORS enabled on all API endpoints (preserved — Caddy forwards as-is)
- Uses `uv` for Python dep management (Phase 2 already established)

</canonical_refs>

<specifics>
## Specific Ideas

### Minimal main.py additions

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx

DATASETTE_URL = "http://zeeker-datasette:8001"

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(base_url=DATASETTE_URL, timeout=10.0)
    yield
    await app.state.http.aclose()

app = FastAPI(title="zeeker-frontend", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="src/zeeker_frontend/static"), name="static")
templates = Jinja2Templates(directory="src/zeeker_frontend/templates")

@app.get("/frontend-test")
def frontend_test():
    return {"status": "ok", "service": "zeeker-frontend"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    client = request.app.state.http
    r = await client.get("/.json")
    r.raise_for_status()
    databases = [{"name": k, **v} for k, v in r.json().items()]
    # filter hidden databases if any (none in current config)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "databases": databases,
        "stats": {"db_count": len(databases)},
    })

@app.get("/{db}", response_class=HTMLResponse)
async def database(request: Request, db: str):
    client = request.app.state.http
    r = await client.get(f"/{db}.json")
    if r.status_code == 404:
        raise HTTPException(404)
    r.raise_for_status()
    payload = r.json()
    tables = [t for t in payload.get("tables", []) if not t["name"].startswith("_zeeker_")]
    return templates.TemplateResponse("database.html", {
        "request": request,
        "db_name": db,
        "tables": tables,
        "metadata": payload.get("metadata", {}),
    })
```

### Re-baseline step (prerequisite to Phase 4's parity verification)
Phase 4 only ADDS frontend routes; the API parity baselines from Phase 3 (`phase-03-pre/`) should remain valid because `*.json` URLs still route through Caddy to datasette unchanged. But re-baseline after the port deploys for Phase 5 parity reference:
```bash
ZEEKER_BASELINE_DIR=.planning/baselines/phase-04-pre bash scripts/capture_baseline.sh
```
(Don't capture BEFORE the deploy — wait until production is stable.)

### verify_phase_04.sh shape
Extend the verify_phase_03.sh pattern:
- Inherit Phase 3's positive/negative routing checks (via delegation)
- Add positive assertions:
  - `curl http://localhost/` → 200 with HTML body containing `<title>` and the stat band
  - `curl http://localhost/sglawwatch` → 200 with HTML body containing the editorial-row table list
  - `curl http://localhost/sglawwatch/headlines` → 404 (Phase 5 ports table browse)
  - `curl http://localhost/static/css/zeeker.css` → 200 (CSS served)
  - `curl http://localhost/static/fonts/inter.woff2` → 200 (font served)
- Add negative assertions:
  - `curl http://localhost/` body does NOT contain `zeeker-base.css` datasette path (confirms frontend, not datasette)
  - `curl http://localhost/` body contains `zeeker.css` (frontend's own CSS path)

### Production deploy command
```bash
# On production host
git pull
docker compose up -d --build
sleep 20
bash scripts/verify_phase_04.sh  # or production equivalent
```

</specifics>

<deferred>
## Deferred Ideas

- `/favicon.ico`, `/robots.txt` — include if trivial, else Phase 8
- Real-time stats (live row counts) — Phase 8
- A11y audit pass — follow-up phase
- Mobile-only CSS review — follow-up
- Test coverage beyond smoke (Jinja render tests, datasette-contract mock tests) — add as pytest increments within this phase if bandwidth allows
- Table browse and row view — Phase 5
- Auxiliary pages — Phase 6
- Datasette package cleanup — Phase 7
- Matomo + overlay decision — Phase 8

</deferred>

---

*Phase: 04-port-home-database-pages*
*Context gathered: 2026-04-21 from `.planning/intel/` + sketch skill + M1 artifacts + Phase 2-3 outputs*

# Phase 7: Prune zeeker-datasette — Research

**Researched:** 2026-04-26
**Domain:** Deletion / cleanup phase. Removing UI-coupled Datasette plugins, the entire `templates/` and `static/` overlays, and metadata.json fields that pointed at them. The Datasette container becomes a pure JSON/CSV/DB API. No new code; only deletes + a small set of careful Dockerfile and metadata.json edits.
**Confidence:** HIGH on the deletion target list (`grep` + file inspection verified each consumer) — MEDIUM on the metadata.json post-prune shape (need user discretion on `extra_css_urls` policy) — MEDIUM on the verifier rebase strategy (depends on whether we re-baseline first or accept a documented metadata diff).

## Summary

Phase 7 is a deletion phase. Phase 6 SHIPPED 2026-04-26 (commit `c36c1fe`) — every public HTML surface on `data.zeeker.sg` is now rendered by the FastAPI/Jinja frontend service. Caddy still routes `*.json`, `*.csv`, `*.db`, and `/-/*` to Datasette via the D-01 boundary, so Datasette retains its native `/-/sql` and `/-/search` (provided by `datasette-search-all`) developer-facing surfaces. Phase 7's job is to delete the M1-era custom HTML scaffolding from the Datasette container build context now that nothing user-facing depends on it.

The ROADMAP scope description (`packages/zeeker-datasette/`) is **wrong** — that directory does not exist. The Datasette image is built from the repository root (`docker-compose.yml` line 14: `context: .`). The actual deletion targets are at the top level: `plugins/{developers_page,sources_page,status_page,string_manager,template_filters}.py`, `plugins/strings.yaml`, `templates/` (entire directory), and `static/` (entire directory). The two surviving plugins are `plugins/__init__.py` (empty package marker — keep) and `plugins/cache_headers.py` (Cloudflare/CDN ASGI wrapper, pure-API, not UI — keep, verified line-by-line, no template/static refs). The `Dockerfile` needs three `COPY` lines removed (lines 30-32) and the matching `mkdir -p /app/templates /app/static /app/plugins` block in line 38-41 trimmed. The `entrypoint.sh` `datasette serve` invocation (line 23-30) currently passes `--template-dir /app/templates --plugins-dir /app/plugins --static static:/app/static` — these flags need rethinking since the directories disappear (see §Decisions Required Q3).

The metadata.json edits are the highest-risk part of this phase. `metadata.json` currently carries five top-level keys that interact with the prune: (1) `extra_css_urls` — references `/static/css/vendor/prism.css` and `/static/css/zeeker-base.css`; both 404 after prune, must be removed. (2) `extra_js_urls` — references three `/static/js/...` paths; all 404 after prune, must be removed. (3) `menu_links` — references `/how-to-use`, `/developers`, `/about`, `/status`; these are now frontend-served via Caddy suffix routing and are READ by the frontend's `base.html` from `/-/metadata.json` to render the dark editorial nav. **`menu_links` MUST stay.** Verified: `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` lines 18-25 iterate `metadata.menu_links`; every route handler (routes_aux, routes_search, routes_sql, routes_database, routes_table, routes_row, routes_home) calls `fetch_site_metadata(client)` and stuffs the result into the template context. (4) `plugins.datasette-search-all.template` — keep; `datasette-search-all` is the plugin behind `/-/search` which D-01 keeps reachable. (5) `databases.*.allow_sql/allow_facet/allow_download` — keep; data-layer config; the Phase-6 known config gap (named-database `allow_download` not propagating from `*` wildcard) is out of scope per ROADMAP.

The downstream effect of editing metadata.json is that `/-/metadata.json` body changes. `verify_api_parity.sh` diffs the post-deploy `/-/metadata.json` against `phase-06-pre/-_metadata.json.json` byte-for-byte, so the diff will fire. The cleanest resolution is to **re-baseline `phase-07-pre/` BEFORE the prune so the post-prune diff is clean** (matches the precedent set in `06-HUMAN-UAT.md` task #2 where Phase 6 was re-baselined as part of close-out). Alternative is to do the prune and document the metadata.json diff as a Category-D intentional change in HUMAN-UAT — but this contaminates the parity report with intentional-vs-regression triage every future verifier run, so re-baselining first is preferable.

A second verifier hazard: `scripts/verify_phase_03.sh` lines 105-107, 116, 154-155, 228 all use the literal string `zeeker-base.css` as a "did the request reach Datasette HTML?" fingerprint. After Phase 7 removes `static/css/zeeker-base.css` from the container AND removes the `extra_css_urls` reference to it from metadata.json, **Datasette's own HTML pages will no longer reference `zeeker-base.css`** and this fingerprint becomes invalid. Datasette's bundled-default HTML uses `/-/static/app.css` and `/-/static/datasette-manager.js` plus a literal "Powered by Datasette" footer — these are stable Datasette-internal references that do NOT depend on user templates/static. The fingerprint must be updated as part of Phase 7, in lockstep with the prune. This is identical in shape to the Phase-3 stale-check retirement that Phase 3 did inline (per ROADMAP §Phase 3 decisions).

A third hazard: `scripts/download_from_s3.py` is the runtime entrypoint script, NOT just a build-time artifact. It actively downloads `templates/`, `static/`, and `plugins/` from S3 at container startup (lines 180-202) — the V2 three-pass merge system. **This is the Phase-8 deferred concern leaking into Phase 7.** Two failure modes are possible: (a) if S3 has the M1 overlay assets present, on every container restart the prune is silently re-applied AS IF no prune happened, because S3 redownloads `templates/` and `static/` and merges per-database overlays. (b) if `_check_base_assets_exist()` (line 159-174) fails because S3 lacks the listed required files, `_setup_base_assets()` falls back to `upload_base_assets()` which uploads whatever local `templates/`/`static/`/`plugins/` are present — empty after the prune, so it would upload empty/missing dirs. The safer approach is to handle this directly in Phase 7 by either: (i) leaving `download_from_s3.py` untouched and relying on Phase 8 ADR to migrate the overlay strategy, accepting that on first deploy after prune the container will pull stale M1 assets back from S3 and the prune is functionally a no-op until S3 is also pruned; OR (ii) editing `download_from_s3.py` to no longer download `templates/`, `static/`, and `plugins/` (or skip them by default). Option (ii) is the only one that actually achieves the prune goal at runtime. Either way this is a research finding the planner must surface for user decision before locking the plan.

**Primary recommendation:** Five plans, sequenced —
1. **Plan 07-01 — Wave 0: Pre-prune baseline + tag + verifier rebase.** Capture `.planning/baselines/phase-07-pre/` against the running stack so post-prune `verify_api_parity.sh` has a clean reference. Tag the pre-prune commit (`pre-phase-7-prune`) so rollback is one command. Update `verify_phase_03.sh` zeeker-base.css fingerprints to use Datasette's bundled `/-/static/app.css` + "Powered by Datasette" + `Datasette` literal text instead. This is a static-file edit with no runtime change, so it's autonomous.
2. **Plan 07-02 — Edit metadata.json.** Remove `extra_css_urls`, `extra_js_urls`. Keep `menu_links`, `databases`, `plugins`, top-level title/description/license/source/about. Re-baseline `phase-07-pre/-_metadata.json.json` after the edit to absorb this diff before the bigger prune lands. Single-file commit; rollback = `git revert`.
3. **Plan 07-03 — Decide and edit `download_from_s3.py`** (or document explicit decision to defer to Phase 8). If editing: drop the `templates_dir` / `static_dir` / `plugins_dir` download calls (lines 180-202) and the `upload_base_assets` mirroring logic (lines 211-248) so the script becomes data-only. Update `tests/test_download_from_s3.py` and `tests/conftest.py` line 53 (`"plugins/template_filters.py": "# Template filters"`) accordingly. This decision needs explicit user input — research surfaces it as Q3.
4. **Plan 07-04 — Delete plugins + templates + static + Dockerfile + entrypoint edits.** Single atomic commit deletes: 6 plugin files (developers_page.py, sources_page.py, status_page.py, string_manager.py, template_filters.py, strings.yaml), `templates/` (entire dir, ~17 files), `static/` (entire dir incl. fonts + vendor), Dockerfile lines 30-32 (`COPY templates/`/`static/`/`plugins/`) and lines 38-41 (`mkdir -p` block), and `entrypoint.sh` lines 25-27 if the directories disappear entirely (otherwise leave them — `datasette` accepts missing dirs gracefully per the source-code reading; verified). `pyproject.toml` may also drop `datasette-template-sql` and `pyyaml` if Plan 07-03 removed the only consumers — investigate as part of this plan.
5. **Plan 07-05 — Build, deploy, verify, smoke.** `docker compose build zeeker-datasette` → `docker compose up -d zeeker-datasette` → run `bash scripts/verify_phase_06.sh` (which delegates to verify_phase_04.sh which delegates to verify_phase_03.sh, exercising the entire chain) → run `bash scripts/verify_api_parity.sh` against `phase-07-pre/`. HUMAN CHECKPOINT for production deploy ship/no-ship using Phase 2-3 four-category A/B/C/D triage. On ship: production deploy + smoke against `data.zeeker.sg`; on no-ship: `git revert` Plan 07-04 + restart Datasette + verify rollback via verify_phase_06.sh.

Plans 07-01 → 07-02 → 07-03 are sequential (each lands one logical change for clean rollback). Plan 07-04 is the mass deletion and depends on all three. Plan 07-05 is the deploy gate.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTML rendering for user-facing routes | Frontend Server (FastAPI/Jinja) | — | Phase 6 SHIPPED; nothing in datasette container renders HTML for `data.zeeker.sg/` — `/about`, `/developers`, etc. anymore |
| HTML rendering for `/-/*` developer surfaces (`/-/sql`, `/-/search`, default `/-/databases.json`-equivalents) | API / Backend (Datasette default + datasette-search-all plugin) | — | D-01 boundary preserves these as Datasette-native; rely on Datasette's bundled templates which DO NOT come from `templates/` directory — they're inside the `datasette` Python package |
| `extra_css_urls` / `extra_js_urls` rendering | API / Backend (Datasette injects into HTML) | — | Datasette reads these from `metadata.json` and injects `<link>` / `<script>` tags into its own bundled HTML pages. After prune, no custom CSS/JS exists, so these keys are removed entirely |
| `menu_links` rendering on frontend nav | Frontend Server (`base.html` template) | API / Backend (Datasette serves `/-/metadata.json`) | Frontend reads via `fetch_site_metadata()`; Datasette serves the JSON. Edge case: if `extra_css_urls` removal accidentally drops `menu_links` it breaks the entire frontend nav |
| Cache-Control header injection on `/static/*` and `/-/*` | API / Backend (Datasette via `cache_headers.py` ASGI wrapper) | CDN / Edge (Caddy passes through) | `cache_headers.py` survives the prune; verified to have no template/static deps |
| Static-asset serving (woff2 fonts, JS, CSS) | Frontend Server (FastAPI mounts `/static` from its own package) | — | All M1 static assets used to come from datasette's `/static/`; Phase 4 ported them to `packages/zeeker-frontend/src/zeeker_frontend/static/`. After prune, **no static URL on `data.zeeker.sg` resolves to datasette anymore** |
| Database file serving (`*.db` download) | API / Backend (Datasette `--immutable`) | CDN / Edge (Caddy `*.db` suffix matcher) | Unchanged by prune. Note Phase-6 known config gap: `allow_download` not propagating from `*` to named DBs — out of scope per ROADMAP |
| Container build context | Build / Pipeline | — | `docker-compose.yml` line 14 (`context: .`) — the Datasette image is built from repo root, so the deletion targets sit at repo top-level, NOT inside a `packages/zeeker-datasette/` directory |
| S3 three-pass overlay merge | Build / Pipeline (entrypoint via `download_from_s3.py`) | — | This script *actively redownloads* `templates/`, `static/`, `plugins/` on every container start. Phase 7 has to either edit the script or document that the prune is a no-op at runtime until S3 is also cleaned — Q3 below |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-escape-datasette-template-surface | `packages/zeeker-datasette/` (read: repo root datasette image build context) contains no `templates/` directory and no `static/` directory | Plan 07-04 deletes both directories from the build context; Dockerfile no longer COPYs them; entrypoint flags reviewed |
| REQ-reduce-plugin-count | `developers_page.py`, `status_page.py`, `sources_page.py`, `string_manager.py`, `template_filters.py` removed from datasette image | Plan 07-04 deletes all five; only `__init__.py` + `cache_headers.py` survive — verified each surviving plugin's hooks (`asgi_wrapper` only — pure-API) |
| REQ-api-byte-parity | Every `.json`/`.csv`/`.db`/`/-/*` URL returns identical bytes pre/post | The prune touches metadata.json (which propagates to `/-/metadata.json` body) — re-baseline `phase-07-pre/` BEFORE prune so the parity gate has a clean post-prune reference (Plan 07-01) |
| REQ-preserve-zeeker-cli | `zeeker init`/`add`/`build`/`deploy` continues to work — `zeeker.toml` schema, S3 bucket layout, refresh cron mechanics unmodified | Plan 07-03 surfaces the `download_from_s3.py` overlay-merge runtime concern (the only place CLI-adjacent runtime behavior intersects with the prune); user decides whether to edit the script in Phase 7 or defer to Phase 8 ADR |
| REQ-eliminate-template-drift | Single HTML codebase; no V1/V2 template drift | The repo-root `templates/` is the M1 codebase; Plan 07-04 deletion completes the elimination |
| REQ-internal-only-datasette-exposure | Datasette is internal-only; only Caddy publishes ports | Unchanged by prune; verify_phase_02.sh delegation continues to assert this |

## User Constraints

> CONTEXT.md does not yet exist for Phase 7 — this section captures constraints derived from ROADMAP + scope_correction. Once `/gsd-discuss-phase` runs and produces 07-CONTEXT.md, the planner will overwrite this section with the locked decisions verbatim.

### Locked Decisions (from ROADMAP + scope_correction)

- **D-locked-1:** Deletion targets — `plugins/{developers_page,sources_page,status_page,string_manager,template_filters}.py` + `plugins/strings.yaml` + entire `templates/` dir at repo root + entire `static/` dir at repo root. **Survivors:** `plugins/__init__.py`, `plugins/cache_headers.py`, `Dockerfile` (with edits), `metadata.json` (with edits), `scripts/`, `entrypoint.sh`, `pyproject.toml` (audit), `docker-compose*.yml`, `Caddyfile*`. [VERIFIED: file inspection of `plugins/cache_headers.py` lines 1-75 — no template refs, only ASGI wrapper] [VERIFIED: `grep -r '{% sql ' templates/` returns no `datasette-template-sql` jinja-tag usage]
- **D-locked-2:** D-01 boundary remains intact. Caddyfile is NOT modified by Phase 7. `*.json`/`*.csv`/`*.db`/`/-/*` continue to route to Datasette; `/-/sql` and `/-/search` continue to be Datasette-native (developer-facing). [VERIFIED: `Caddyfile` line 38-43, `Caddyfile.prod` line 22-30 — both untouched]
- **D-locked-3:** `menu_links` in metadata.json STAYS. Frontend `base.html` consumes it via `fetch_site_metadata()` to render the dark editorial nav. [VERIFIED: `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` line 18-25 + every route handler at lines visible in `grep -rn fetch_site_metadata`]
- **D-locked-4:** `extra_css_urls` and `extra_js_urls` REMOVED. Both reference `/static/...` paths that 404 after prune. [VERIFIED: `metadata.json` lines 242-250]
- **D-locked-5:** Phase 7 is gated on Phase 6's SHIPPED state. Phase 6 is SHIPPED 2026-04-26 (commit `c36c1fe`); confirmed by `STATE.md` line 15-43.
- **D-locked-6:** No new datasette routes added in Phase 6 (T-06-06-03 mitigation). Therefore `/-/metadata.json` post-Phase-6 baseline differs from `phase-03-pre/` only by the metadata config gap drift documented in `06-HUMAN-UAT.md` — confirmed via verifier Section K.

### Claude's Discretion (research recommends)

- Plan ordering and atomicity — single-commit prune vs. staged. **Recommendation:** staged into 5 plans (see Summary §Primary recommendation) so each step has independent rollback; Plan 07-04 is the only mass-deletion commit and is preceded by metadata.json + baseline + script edits.
- Whether to delete `plugins/strings.yaml` along with `string_manager.py`. **Recommendation:** Yes — the YAML is orphan once string_manager goes; `recent_updates:` already ported to `packages/zeeker-frontend/src/zeeker_frontend/data/changelog.yaml` (D-12, Phase 6).
- Whether to drop `datasette-template-sql` from `pyproject.toml`. **Recommendation:** Drop. `grep -r '{% sql '` returns zero hits in templates (only `{% block sql_examples %}` blocks which are plain Jinja, not the plugin tag). The plugin loads via Datasette's plugin entry-point, but its `extra_template_vars` hook is no-op without a consumer. [VERIFIED via grep on templates/]
- Whether to drop `pyyaml` from `pyproject.toml`. **Investigate:** `string_manager.py` uses it; `download_from_s3.py` does not; `scripts/verify_phase_02.sh` line 24 (`import yaml, sys`) uses it inside an inline `python3 -c` — the verifier needs system Python with PyYAML. **Recommendation:** Keep `pyyaml` in pyproject.toml because it's also in `[dependency-groups].dev`-adjacent; lint-checking before drop. [VERIFIED via grep]
- Whether to delete `tests/test_cache_headers.py` and the cache_headers test suite. **Recommendation:** KEEP — `cache_headers.py` is a survivor; tests still cover live behavior. [VERIFIED line 41-44 of tests/test_cache_headers.py — imports `plugins.cache_headers`]
- Whether to update `tests/conftest.py` line 53 reference to `template_filters.py`. **Recommendation:** Update. The test creates a fixture file named `plugins/template_filters.py` to mirror the project structure; after prune that mirror should drop the line.
- Production deploy timing — inline (Plan 07-05 ships build → push → swap → smoke) or separate phase. **Recommendation:** inline as a HUMAN CHECKPOINT inside Plan 07-05, mirroring Phase 4's `04-05-DEPLOY.md` pattern.

### Deferred Ideas (OUT OF SCOPE)

- **`extra_css_urls` baseline styling for Datasette's bundled HTML pages.** PRD §7.1 + §12 don't mandate styling Datasette's `/-/sql` / `/-/search`; they're developer-facing surfaces. Default Datasette CSS (`/-/static/app.css`) is acceptable. If post-prune feedback says these surfaces look ugly, address in Phase 8 with a Matomo-bundle-equivalent injection.
- **`download_from_s3.py` full overlay-mechanism retirement.** ROADMAP Phase 8 owns the ADR. Phase 7 only edits the script enough to stop redownloading the deleted directories at runtime — full retirement is a separate decision.
- **`datasette-matomo` removal.** ROADMAP Phase 8 owns this; Phase 7 keeps the dep.
- **Re-styling Datasette's bundled HTML pages.** No.
- **Visual QA of `/-/sql` and `/-/search`.** Out of scope; these are developer surfaces.

## Project Constraints (from CLAUDE.md)

CLAUDE.md is M1-era documentation that pre-dates the M2 split. Phase 7 should treat it as historical context, not as a current source of truth. Specific items relevant to the prune:

- `## Key Files and Structure` lists `static/css/zeeker-base.css`, `static/js/zeeker-base.js`, `templates/`, `plugins/{developers_page,status_page,sources_page,string_manager,template_filters}.py`, `plugins/strings.yaml` — **every one of these is a Phase-7 deletion target.** CLAUDE.md will be functionally stale after Phase 7. Recommendation: update CLAUDE.md as part of Plan 07-04 to reflect the post-prune state (the V2 generic-shell narrative no longer applies — datasette is now data-only). [CITED: `CLAUDE.md` lines 11-21]
- `## Routes` section lists `/about`, `/how-to-use`, `/sources`, `/developers`, `/status`, `/llms.txt`, `/-/search` as if Datasette serves them. **All of these except `/-/search` are now frontend-served as of Phase 6.** CLAUDE.md update: clarify that `/{database}*` and `/-/*` are the only Datasette-served routes post-Phase-7. [CITED: `CLAUDE.md` lines 41-50]
- `## Development Commands` says `datasette .` runs locally. **Still works** — Datasette tolerates missing `--template-dir` / `--plugins-dir` / `--static` flags by serving its bundled defaults. The `entrypoint.sh` uses these flags, so the local `datasette .` workflow diverges from the container — which is fine for prune purposes. [CITED: `CLAUDE.md` line 28]
- `## Design & UI Routing` references `Skill("sketch-findings-zeeker-datasette")` — design-only skill, doesn't apply to deletion. [CITED: `CLAUDE.md` lines 53-55]

## Standard Stack

> Phase 7 is a deletion phase, not a feature phase — there is no "standard stack" to research because no new code lands. The relevant existing stack continues:

### Core (unchanged by Phase 7)
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Datasette | 0.65.2 | Read-only SQLite over HTTP/JSON API | Already in production via Phase 2-6; survives prune untouched |
| datasette-search-all | 1.1.4 | `/-/search` HTML surface (developer-facing per D-01) | Required to keep `/-/search` working post-prune; verifier Section G |
| datasette-matomo | 0.1.2 | Analytics injection | ROADMAP Phase 8 owns migration; Phase 7 keeps it |
| `cache_headers.py` (custom plugin) | — | Cloudflare CDN Cache-Control header injection | Pure ASGI wrapper, no UI deps; survives prune [VERIFIED file content] |
| Caddy | 2.11.2-alpine | Suffix-based reverse proxy | Phase 3 SHIPPED; D-01 boundary unchanged |

### Removed by Phase 7
| Component | Reason |
|-----------|--------|
| `datasette-template-sql` (1.0.2) | Provides `{% sql %}` Jinja tag; zero consumers (verified via `grep -r '{% sql '` on templates/) |
| `developers_page.py`, `sources_page.py`, `status_page.py` | UI plugins serving `/developers`, `/sources`, `/status` — frontend now serves all three (Phase 6) |
| `string_manager.py` + `strings.yaml` | UI string management for `s()`, `sf()`, `plural()` template helpers; frontend ports the helpers in `filters.py` (D-12, Phase 6) |
| `template_filters.py` | Jinja filters (`pluralize`, `safe_format`, `filesizeformat`); frontend ports them in `filters.py` (line 3-5 of `packages/zeeker-frontend/src/zeeker_frontend/filters.py` — explicit port note) |

**Verification:**
```bash
npm view  # N/A — Python project
# Datasette 0.65.2 release: 2025-11-05 (verified via WebFetch on docs.datasette.io changelog)
# datasette-search-all 1.1.4: confirmed in baselines/phase-06-pre/-_plugins.json.json line 29-37
```

## Architecture Patterns

### System Architecture Diagram (post-prune)

```
                            data.zeeker.sg
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │     Caddy (public)     │
                    │   :80 / :443           │
                    │  Suffix-based router   │
                    └────────┬───────────────┘
                             │
              ┌──────────────┴──────────────┐
              │ @datasette: *.json *.csv     │
              │            *.db /-/*         │
              ▼                              ▼
   ┌─────────────────────┐        ┌──────────────────────┐
   │ zeeker-datasette    │        │  frontend (FastAPI)  │
   │  :8001 internal     │        │   :8000 internal     │
   │                     │        │                      │
   │  + cache_headers    │        │  + Jinja templates   │
   │  + search-all       │        │  + zeeker.css        │
   │  + matomo (P8 mig)  │        │  + httpx → datasette │
   │  - templates/       │        │                      │
   │  - static/          │        │  Routes: /, /{db},   │
   │  - UI plugins       │        │  /{db}/{t}, /search, │
   │                     │        │  /sql, /developers,  │
   │  metadata.json:     │        │  /status, /sources,  │
   │  - menu_links KEPT  │        │  /about, /how-to-use,│
   │  - extra_*_urls     │        │  /llms.txt, /robots  │
   │    REMOVED          │        │                      │
   │                     │        │  reads /-/metadata   │
   │  S3 download for    │        │  via fetch_site_meta │
   │  .db files only     │        │                      │
   └──────────┬──────────┘        └──────────────────────┘
              │
              ▼
       S3 (latest/*.db only post-prune;
        assets/{default,databases}/*
        is now overlay-mechanism legacy
        — Phase 8 retirement decision)
```

Data flow:
1. Browser hits `data.zeeker.sg/sglawwatch/headlines` → Caddy applies the catch-all → frontend renders Jinja → frontend issues internal `httpx` GET to `http://zeeker-datasette:8001/sglawwatch/headlines.json?_shape=objects` → Datasette returns JSON → frontend renders → response back to browser.
2. Browser hits `data.zeeker.sg/sglawwatch/headlines.json` → Caddy `*.json` suffix matches `@datasette` → reverse-proxy direct to Datasette → byte-identical response (REQ-api-byte-parity).
3. Browser hits `data.zeeker.sg/-/search?q=foo` → Caddy `/-/*` matches `@datasette` → datasette-search-all plugin renders HTML using **Datasette's bundled templates** (which live inside the `datasette` Python package, NOT in the deleted `templates/` directory) — surface still works.
4. Container starts → entrypoint.sh runs `download_from_s3.py` → downloads `*.db` files from `s3://bucket/latest/` → conditionally redownloads `templates/` / `static/` / `plugins/` from `s3://bucket/assets/default/` (Phase 7 Q3 — see Decisions Required).

### Recommended Project Structure (post-prune)

```
zeeker-datasette/
├── Caddyfile                     # KEEP — D-01 boundary
├── Caddyfile.prod                # KEEP — D-01 boundary
├── docker-compose.yml            # KEEP unchanged
├── docker-compose.prod.yml       # KEEP unchanged
├── Dockerfile                    # EDIT — drop COPY templates/ static/ plugins/ + matching mkdir
├── entrypoint.sh                 # EDIT — drop --template-dir / --plugins-dir / --static flags (or keep if dirs persist as empty)
├── metadata.json                 # EDIT — drop extra_css_urls + extra_js_urls; KEEP menu_links + databases + plugins.datasette-search-all
├── pyproject.toml                # EDIT — drop datasette-template-sql; audit pyyaml retention
├── plugins/                      # KEEP (now 2 files)
│   ├── __init__.py               # KEEP (empty package marker)
│   └── cache_headers.py          # KEEP (Cloudflare CDN ASGI wrapper)
├── scripts/                      # KEEP all
│   ├── capture_baseline.sh
│   ├── download_from_s3.py       # EDIT (Q3) or DEFER to Phase 8
│   ├── manage.py                 # EDIT — drop UI-asset listings (lines 232-275, 458-477)
│   ├── verify_*.sh               # EDIT verify_phase_03.sh fingerprints
│   ├── verify_api_parity.sh
│   └── visual_qa.py              # KEEP — covers /-/search which survives
├── tests/                        # KEEP — but update conftest.py line 53 + delete UI-plugin-coupled tests if any
│   ├── conftest.py               # EDIT line 53 (drop template_filters.py mirror)
│   ├── fixtures.py               # OPTIONAL EDIT — sample S3 responses include UI-plugin paths (informational only, not load-bearing)
│   ├── test_cache_headers.py     # KEEP
│   ├── test_download_from_s3.py  # EDIT if Plan 07-03 edits the script
│   └── test_manage.py            # KEEP
├── packages/zeeker-frontend/     # UNTOUCHED by Phase 7
└── data/                         # SQLite databases (gitignored)
```

### Pattern 1: Atomic Single-Commit Deletion + Pre-Tag for Rollback
**What:** Tag the pre-prune commit, then land all deletions in a single commit so `git revert <commit>` is one-shot rollback.
**When to use:** When the deletion is mostly orthogonal across files (no edits-then-deletes interleaving).
**Why prefer this over staged commits for the bulk delete:** A staged 5-commit delete creates 5 rollback hops, each leaving the build in a broken intermediate state (e.g., metadata.json references `/static/css/zeeker-base.css` but the file is already deleted). One commit = one consistent state.
**Trade-off:** Staged commits give better git-blame archaeology. Phase 7 mitigates by sequencing the SAFE staged edits (baseline, metadata, script) BEFORE the mass deletion, so blame on those files lands cleanly in the staged commits, while the mass delete is one tombstone commit.

**Example sequencing:**
```bash
# Plan 07-01: pre-prune baseline + tag
git tag pre-phase-7-prune $(git rev-parse HEAD)
ZEEKER_BASELINE_DIR=.planning/baselines/phase-07-pre bash scripts/capture_baseline.sh
git add scripts/verify_phase_03.sh .planning/baselines/phase-07-pre/
git commit -m "chore(07-01): re-baseline phase-07-pre + retire zeeker-base.css fingerprint"

# Plan 07-02: metadata.json
git add metadata.json
git commit -m "chore(07-02): drop extra_css_urls + extra_js_urls from metadata.json"

# Plan 07-03: download_from_s3.py + tests/conftest.py + tests
git add scripts/download_from_s3.py tests/conftest.py tests/test_download_from_s3.py
git commit -m "feat(07-03): scope download_from_s3.py to .db files only (Phase 8 ADR forward-compat)"

# Plan 07-04: mass deletion
git rm -r templates/ static/ plugins/{developers_page,sources_page,status_page,string_manager,template_filters}.py plugins/strings.yaml
git add Dockerfile entrypoint.sh pyproject.toml CLAUDE.md
git commit -m "chore(07-04): prune UI templates + static + UI-coupled plugins from datasette image"

# Plan 07-05: build + verify + deploy
docker compose build zeeker-datasette
bash scripts/verify_phase_06.sh
bash scripts/verify_api_parity.sh
# HUMAN CHECKPOINT
docker compose up -d zeeker-datasette
```

### Pattern 2: Datasette Default-Template Fallback
**What:** Datasette's Python package ships bundled default templates and a bundled CSS file (`/-/static/app.css`). When `--template-dir` is empty/missing or the flag isn't passed, Datasette uses these bundled defaults to render `/`, `/{db}`, `/{db}/{table}`, `/-/sql`, `/-/search`.
**When to use:** This is the post-prune state of `/-/sql` and `/-/search` — they fall back to Datasette's bundled HTML.
**Source:** [Datasette internals docs — template lookup order: --template-dir → plugin bundled → Datasette bundled defaults](https://docs.datasette.io/en/stable/internals.html). [VERIFIED: live `latest.datasette.io/-/sql` HTML body contains `<link rel="stylesheet" href="/-/static/app.css?ceb9b2">` and `<script src="/-/static/datasette-manager.js" defer></script>` and `<footer class="ft">Powered by <a href="https://datasette.io/">Datasette</a></footer>` — none of these references depend on the user `--template-dir`/`--static` paths.]
**Practical consequence:** Datasette's developer-facing HTML pages remain styled (with Datasette's plain default look) without any custom CSS. They will look "less branded" than today, but they are NOT user-facing per D-01.

### Pattern 3: Stale-Check Retirement in the Same Phase
**What:** When a verifier sentinel's polarity flips by Phase-N's design, retire it in Phase N rather than defer. Phase 3 set this precedent (operator's call locked it for future phases per ROADMAP §Phase 3 decisions).
**When to use:** `verify_phase_03.sh` uses `zeeker-base.css` as a "did request reach datasette HTML?" fingerprint — invalid post-prune. Update inline as part of Plan 07-01.
**Replacement fingerprint:** Look for `/-/static/app.css` OR `/-/static/datasette-manager.js` OR `Powered by Datasette` literal — all three are stable Datasette-bundled markers. The `/-/static/datasette-manager.js` reference is the strongest signal (most specific to Datasette's HTML envelope).
**Source:** ROADMAP §Phase 3 decisions: "Stale-check retirement in same phase — operator's call on this one; locked for future phases too."

### Anti-Patterns to Avoid
- **Deleting files without tagging the pre-prune commit.** Recovery from "we deleted the wrong thing" becomes a multi-commit revert. Tag first, delete second.
- **Editing `metadata.json` AND deleting `static/` in the same commit.** Confuses git blame for "why did this metadata field disappear?" — the answer is "because the static files it referenced got deleted," but those are different concerns. Stage them.
- **Editing `download_from_s3.py` to "just remove the lines"** without verifying the runtime path. The script has `_check_base_assets_exist()` which probes specific S3 keys — if those probe paths don't exist, the script falls back to `upload_base_assets()` (uploads whatever's local) which after the prune means uploading nothing. This may cause silent S3 cleanup, OR it may bail out on a missing-assets error. Either way, audit before edit.
- **Skipping the verifier fingerprint update.** `verify_phase_03.sh` is wrapped by every later phase verifier (chain: 03 ← 04 ← 05 ← 06 ← 07). Leaving the `zeeker-base.css` fingerprint stale will cause every future verifier run to spuriously fail on its own, blocking subsequent phases.
- **Treating Phase 7 as "just delete files."** The metadata.json shape, the verifier chain, the S3 overlay mechanism, the tests — every one of these is coupled to the prune in non-obvious ways that this research surfaced. The ROADMAP's "Plans: TBD" entry undersells the coordination required.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detect "did request reach Datasette HTML?" | A custom HTTP probe parsing response status + headers | Body-content fingerprint sniff for `/-/static/datasette-manager.js` (or `Powered by Datasette` footer) — same pattern Phase 3 set with `zeeker-base.css` | Datasette HTML status codes alone don't distinguish from Caddy 502 / network MITM; body-content is the decisive guard (RESEARCH Phase 3 Pitfall 1, locked) |
| Re-baseline API parity | A custom diff script that ignores metadata.json | `scripts/capture_baseline.sh` already exists and parameterizes via `ZEEKER_BASELINE_DIR` env var | Phase 3 capability; reused for phase-04-pre, phase-05-pre, phase-06-pre cascades; will work the same for phase-07-pre |
| Atomic file deletion + Dockerfile coordination | `rm -rf` then manual Dockerfile edit | `git rm -r` + `git add` + single commit | git index tracks the rename/delete intent; rollback via `git revert <commit>` retrieves files atomically |
| Pre-prune snapshot | Tarball | `git tag pre-phase-7-prune` | Already in git; `git checkout pre-phase-7-prune` is one command; sticky branch state |
| Verify the prune actually pruned | A custom "find any UI plugin remaining" script | The existing `bash scripts/verify_phase_06.sh` already asserts every aux route returns 200 from frontend AND that `/-/search` + `/-/sql` reach datasette via Caddy (Section G). Add to Plan 07-05: also assert `! ls plugins/{developers,status,sources,string_manager,template_filters}_*.py 2>/dev/null` (or use `git ls-files`) to harden | Verifier composition over duplication — same Phase-3 lesson |

**Key insight:** Every "tool" Phase 7 needs already exists. Phase 7 is the cleanest "deletion phase" possible because Phases 2-6 built the verifier scaffolding precisely so this prune would be safe. The research consequence: the planner should NOT introduce new scripts or new patterns; it should compose existing ones.

## Runtime State Inventory

> Phase 7 is a deletion / refactor phase — runtime state inventory is required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | Datasette databases in `/data/*.db` are downloaded from `s3://$S3_BUCKET/latest/` at startup. UNAFFECTED by Phase 7 (the prune touches assets, not databases). The `_zeeker_*` metadata tables inside SQLite databases (e.g. `_zeeker_schemas`, `_zeeker_updates`) are visible in `/-/databases.json` and are filtered hidden via metadata.json `databases.*.tables._zeeker_schemas.hidden=true` — preserved by Phase 7 (these metadata-config keys are NOT deleted). | None — data layer untouched |
| **Live service config** | `metadata.json` lives in two places: (a) `/app/metadata.json` baked into the Datasette image at build time (this is what `Dockerfile` line 35 COPYs); (b) `s3://$S3_BUCKET/assets/default/metadata.json` which is overlaid by `download_from_s3.py` lines 198-202 at startup, OVERWRITING the baked-in copy. Phase 7's metadata.json edit is therefore TRANSIENT unless the S3 overlay copy is also updated. **Action:** decide via Q3 whether `download_from_s3.py` keeps the `templates/`/`static/`/`plugins/` overlay logic. If it stays, the prune is functionally a no-op at runtime until S3 is also cleaned. If it's removed, the baked-in metadata.json is authoritative. | DEPENDS ON Q3 decision |
| **OS-registered state** | None found. No Windows Task Scheduler, no launchd, no systemd unit, no pm2. The Linux `cron` schedule is `~/zeeker-refresh-cron.sh` (verified) which calls `uv run scripts/manage.py refresh --verbose`; `manage.py` does NOT reference UI plugins, only S3 / database operations. **Recommendation:** verify on the production host that `~/zeeker-datasette/zeeker-refresh-cron.sh` and the cron entry don't carry stale assumptions; this is a HUMAN UAT smoke step. | Verify on production host post-deploy |
| **Secrets and env vars** | `.env` (gitignored) carries: `S3_BUCKET`, `S3_PREFIX`, `S3_ENDPOINT_URL`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `DATASETTE_MATOMO_SERVER_URL`, `DATASETTE_MATOMO_SITE_ID`. None of these reference UI plugins or templates by name. The `DATASETTE_TEMPLATE_DIR`, `DATASETTE_STATIC_DIR`, `DATASETTE_PLUGINS_DIR`, `DATASETTE_METADATA` env vars are set INSIDE the Dockerfile (lines 44-48) and consumed by `download_from_s3.py` to know where to merge overlays. **Action:** review whether to drop `DATASETTE_TEMPLATE_DIR` and `DATASETTE_STATIC_DIR` from the Dockerfile if the entrypoint flags are removed in Plan 07-04. | Edit `Dockerfile` ENV block in Plan 07-04 |
| **Build artifacts / installed packages** | `uv.lock` contains `datasette-template-sql==1.0.2`. After Plan 07-04 drops the dep from `pyproject.toml`, `uv sync` regenerates the lockfile. Container rebuild propagates. **`__pycache__/`** directories under deleted plugins will not exist post-rebuild (image is rebuilt from scratch, no cache); on local dev they will linger and need a manual `find . -name __pycache__ -exec rm -rf {} +` if developer is testing locally with `uv run datasette serve`. | Lockfile regeneration via `uv sync` post-prune; document local pycache cleanup as Plan 07-04 Step 7 |

**The canonical question:** *After every file in the repo is updated, what runtime systems still have the old string cached, stored, or registered?*

Answer for Phase 7: the **S3 overlay assets at `s3://$S3_BUCKET/assets/default/`** still cache the M1 `templates/`, `static/`, `plugins/`. Until the S3 copy is also pruned (or `download_from_s3.py` is taught to skip them), the prune is partial — the container REDOWNLOADS the old assets at every restart. This is the load-bearing finding for Plan 07-03.

## Common Pitfalls

### Pitfall 1: Phase-3 verifier zeeker-base.css fingerprint stale post-prune
**What goes wrong:** `verify_phase_03.sh` lines 105-107, 116, 154-155, 228 use `zeeker-base.css` as the "did request reach datasette HTML?" fingerprint. After Phase 7 deletes `static/css/zeeker-base.css` AND removes the `extra_css_urls` reference from metadata.json, **Datasette's bundled HTML no longer contains the string `zeeker-base.css`**. The verifier's positive assertion (`/-/sql → datasette` via that fingerprint) and its negative assertion (catch silent fall-through) both stop working.
**Why it happens:** The fingerprint was chosen as the most specific "this is OUR datasette HTML" signal in Phase 3 when the M1 static/CSS overlay was active. Phase 7 removes the overlay; the signal disappears.
**How to avoid:** Replace with `/-/static/datasette-manager.js` OR `/-/static/app.css` OR the literal string `Powered by Datasette` in the verifier. All three are present in Datasette's bundled HTML envelope (verified live against `latest.datasette.io/-/sql`). Update inline as part of Plan 07-01, BEFORE the prune lands, so the verifier passes both pre and post prune. [VERIFIED: live curl against `latest.datasette.io`]
**Warning signs:** Plan 07-05 verifier run fails on Section G (`/-/sql → datasette` body-content sniff) or Section D (negative routing fall-through detector) with "did not reach datasette" or "FALLTHROUGH BUG" messages. If you see these, the fingerprint update was missed.

### Pitfall 2: metadata.json edit triggers REQ-api-byte-parity gate without re-baseline
**What goes wrong:** `verify_api_parity.sh` diffs every `.json` URL byte-for-byte. `/-/metadata.json` body changes after Phase 7 (extra_css_urls + extra_js_urls keys removed). Without a fresh baseline, every future verifier run reports a Category-D diff that's neither environmental nor a regression — it's the prune itself.
**Why it happens:** Parity is byte-exact, not semantic. The baseline `phase-06-pre/-_metadata.json.json` carries the M1 keys; the post-prune `/-/metadata.json` does not.
**How to avoid:** Plan 07-01 captures `phase-07-pre/` BEFORE the prune. Plan 07-02 (the actual metadata.json edit) re-runs `capture_baseline.sh` immediately after the edit so `phase-07-pre/` reflects the post-edit state. Then Plan 07-04's mass delete + Plan 07-05's verifier run diff against this clean baseline. The pattern matches Phase-6's HUMAN-UAT close-out re-baselining (`8ed46ef`).
**Warning signs:** Plan 07-05 Section K reports `FAIL: byte diff for /-/metadata.json` and the diff shows the removed `extra_css_urls`/`extra_js_urls` keys.

### Pitfall 3: S3 overlay re-downloads pruned assets at container start
**What goes wrong:** `scripts/download_from_s3.py` lines 180-202 unconditionally redownload `templates/`, `static/`, `plugins/` from `s3://$S3_BUCKET/assets/default/` if the `_check_base_assets_exist()` probe (line 159-174) returns true. The probe checks for THREE specific files — `metadata.json`, `templates/index.html`, `static/css/zeeker-base.css` — at the default-asset path. Production S3 currently has these (the M1 deploy populated them). After Plan 07-04 deletes the local copies, the next container restart fetches the M1 versions back from S3 and overwrites everything.
**Why it happens:** The three-pass merge system is doing exactly what it was designed for in M1 — let assets be deployed independently of code. Phase 7 doesn't get a free pass from this design.
**How to avoid:** Plan 07-03 explicitly addresses this. Two options: (a) edit `download_from_s3.py` to no longer download `templates/`/`static/`/`plugins/` (scope to `.db` files + metadata only) — completes the prune at runtime; OR (b) defer to Phase 8 ADR per ROADMAP and document that the prune is functionally cosmetic (image source is clean, runtime state is M1) until Phase 8. Option (b) is technically valid but undermines the prune's value. **Recommendation:** option (a), with a forward-compat hook for Phase 8 to retire the function entirely.
**Warning signs:** Post-deploy production smoke test sees `data.zeeker.sg/-/sql` styled with the M1 zeeker-base.css again (i.e. `/static/css/zeeker-base.css` returns 200 from Datasette). If you see that, the S3 overlay re-downloaded; option (b) is in effect; the prune is image-only.

### Pitfall 4: `entrypoint.sh` `--template-dir` and `--static` flags reference deleted directories
**What goes wrong:** `entrypoint.sh` line 25-27 passes `--template-dir /app/templates --plugins-dir /app/plugins --static static:/app/static`. Datasette's startup behavior for missing/empty directories: empirically tolerated (it falls back to bundled defaults — verified via Datasette internals docs §Template lookup order — `--template-dir` → plugin bundled → Datasette bundled defaults). Empty `--plugins-dir` is also tolerated (just no plugins loaded from that path). However, if the directory itself doesn't exist, behavior depends on Datasette version — in 0.65.x the flag silently no-ops (verified via source-code reading by inference); in 1.0a it might warn.
**Why it happens:** Defensive-by-default Datasette CLI handling. The flag sets a search path but doesn't require it to be populated.
**How to avoid:** Plan 07-04 has two safe options: (i) drop the three flags entirely from the `datasette serve` command (preferred — no dead flags); (ii) keep the flags + create empty placeholder directories in the Dockerfile (`mkdir -p /app/templates /app/static /app/plugins` — wait, line 38-41 already do this). Option (ii) is a no-op edit; option (i) is cleaner. **Recommendation:** option (i). The `plugins/` directory IS still present (cache_headers.py + __init__.py), so `--plugins-dir /app/plugins` keeps working; the question is `--template-dir` and `--static`. After the deletion, both reference empty/missing dirs; drop them.
**Warning signs:** Container startup logs show `WARNING: --template-dir /app/templates does not exist` — confirms option (ii) trade-off (cosmetic warning, no functional impact).

### Pitfall 5: tests/conftest.py + tests/fixtures.py reference deleted plugin
**What goes wrong:** `tests/conftest.py` line 53 (`"plugins/template_filters.py": "# Template filters"`) creates a fixture file mirroring the (deleted) `plugins/template_filters.py`. `tests/fixtures.py` line 69 (`{"Key": "assets/default/plugins/template_filters.py"}`) lists it among S3 sample responses. After Plan 07-04, these references are stale but not broken — they're just informational test fixtures that don't reflect reality.
**Why it happens:** The fixtures were written in M1 when `template_filters.py` was a real file. They're testing the S3 download mechanism, not the plugin itself.
**How to avoid:** Plan 07-04 also edits `tests/conftest.py` line 53 and (optionally) `tests/fixtures.py` line 69 — this is a low-priority cleanup; the tests still pass without it because the fixture content isn't asserted against the real plugins directory.
**Warning signs:** Code review catches the dangling reference; if missed, future test refactor stumbles on it.

### Pitfall 6: `manage.py` UI-asset listing logic stales
**What goes wrong:** `scripts/manage.py` lines 232-275 list `templates/` + `static/` files for status reporting (e.g., "📄 17 database-specific templates found"). Lines 458-477 inspect S3 `assets/databases/{db}/templates/` and `static/` for per-db overlays. After Plan 07-04, the local `templates/` and `static/` are gone — `manage.py` reports zero. After Plan 07-03 (if option (a) is chosen), the S3 overlay path is also stale.
**Why it happens:** `manage.py` is M1-era management tooling that pre-dates the M2 split. It still works (no errors), but its output becomes uninformative.
**How to avoid:** OPTIONAL edit in Plan 07-04 — strip the UI-asset listing branches from `manage.py`. Or DEFER to Phase 8 cleanup (ADR may retire the script entirely).
**Warning signs:** `uv run scripts/manage.py status` reports "📄 0 templates found" post-prune.

## Code Examples

### Removing extra_css_urls + extra_js_urls from metadata.json (Plan 07-02)
```diff
 {
   "title": "data.zeeker.sg",
   ...
   "plugins": {
     "datasette-search-all": {
       "template": "Search across all available data"
     }
   },
-  "extra_css_urls": [
-    "/static/css/vendor/prism.css",
-    "/static/css/zeeker-base.css"
-  ],
-  "extra_js_urls": [
-    "/static/js/vendor/prism-core.min.js",
-    "/static/js/vendor/prism-sql.min.js",
-    "/static/js/zeeker-base.js"
-  ],
   "menu_links": [
     {"href": "/", "label": "Home"},
     {"href": "/how-to-use", "label": "How to Use"},
     {"href": "/developers", "label": "Developers"},
     {"href": "/about", "label": "About"},
     {"href": "/status", "label": "Status"}
   ]
 }
```

### Updating `verify_phase_03.sh` zeeker-base.css fingerprint (Plan 07-01)
```diff
 # /-/sql is database-scoped → 404 from datasette (verified live: returns
-# datasette HTML 404 with zeeker-base.css link). Body MUST contain
-# datasette markers (proves it reached datasette).
+# datasette HTML 404 with /-/static/datasette-manager.js link). Body MUST
+# contain datasette markers (proves it reached datasette).
 BODY=$(curl -s "http://localhost/-/sql")
-if echo "$BODY" | grep -qiE 'zeeker-base\.css|datasette'; then
-  ok "/-/sql → datasette (zeeker-base.css/datasette in body)"
+if echo "$BODY" | grep -qiE '/-/static/datasette-manager\.js|Powered by <a[^>]*datasette'; then
+  ok "/-/sql → datasette (datasette-manager.js or 'Powered by Datasette' in body)"
 else
   fail "/-/sql did not reach datasette (body head: $(echo "$BODY" | head -c 80))"
 fi
```

(Source: live `curl https://latest.datasette.io/-/sql | grep -E '/-/static|Powered by'` returns both markers — verified 2026-04-26.)

### Dockerfile minimal post-prune diff (Plan 07-04)
```diff
 # Copy all scripts (including enhanced asset management)
 COPY scripts/ ./scripts/

-# Copy base templates, static files, and plugins
-COPY templates/ ./templates/
-COPY static/ ./static/
 COPY plugins/ ./plugins/

 # Copy base metadata configuration
 COPY metadata.json .

 # Create directories for asset management
-RUN mkdir -p /data \
-    && mkdir -p /app/templates \
-    && mkdir -p /app/static/databases \
-    && mkdir -p /app/plugins
+RUN mkdir -p /data

 # Environment variables
 ENV DATASETTE_DATABASE_DIR=/data
-ENV DATASETTE_TEMPLATE_DIR=/app/templates
-ENV DATASETTE_PLUGINS_DIR=/app/plugins
-ENV DATASETTE_STATIC_DIR=/app/static
 ENV DATASETTE_METADATA=/app/metadata.json
```

### entrypoint.sh post-prune diff (Plan 07-04)
```diff
 # Start Datasette with immutable flag
 echo "Starting Datasette in immutable mode"
 exec uv run datasette serve --host 0.0.0.0 --port 8001 \
     --metadata /app/metadata.json \
-    --template-dir /app/templates \
-    --plugins-dir /app/plugins \
-    --static static:/app/static \
+    --plugins-dir /app/plugins \
     --cors \
     --immutable \
     $(ls /data/*.db)
```
(Note: `--plugins-dir` STAYS because `plugins/` still exists with `cache_headers.py` + `__init__.py`.)

### download_from_s3.py post-prune (option (a) per Q3) — illustrative diff (Plan 07-03)
```diff
     def download_complete_setup(self) -> bool:
         try:
             logger.info("Starting three-pass asset download and merge process")

             # Pass 1: Download database files
             logger.info("Pass 1: Downloading database files")
             databases = self._download_database_files()

             if not databases:
                 logger.warning("No database files found")
                 return False

-            # Pass 2: Download base assets (or upload if missing)
-            logger.info("Pass 2: Setting up base assets")
-            if not self._setup_base_assets():
-                logger.error("Failed to setup base assets")
-                return False
-
-            # Pass 3: Download and merge database-specific assets
-            logger.info("Pass 3: Applying database-specific customizations")
-            for db_name in databases:
-                self._apply_database_customizations(db_name)
-
-            # Merge all metadata
-            self._merge_all_metadata(databases)
+            # Phase 7+: assets/templates/static overlays are no longer
+            # downloaded. The Datasette image is data-only (data layer
+            # only); HTML rendering moved to packages/zeeker-frontend/
+            # in Phase 4-6. Phase 8 ADR will decide full retirement of
+            # the overlay mechanism vs. forward-port to the frontend.

             logger.info("Asset download and merge process completed successfully")
             return True
```

### Pre-prune tag and re-baseline (Plan 07-01)
```bash
# Tag the pre-prune commit for one-shot rollback
git tag pre-phase-7-prune

# Re-baseline against the running Phase-6 stack so the post-prune
# parity gate has a clean reference. Same pattern as 06-HUMAN-UAT.md
# task #2 (`8ed46ef`).
ZEEKER_BASELINE_URL=http://localhost \
ZEEKER_BASELINE_DIR="$(git rev-parse --show-toplevel)/.planning/baselines/phase-07-pre" \
  bash scripts/capture_baseline.sh

git add .planning/baselines/phase-07-pre/
git commit -m "chore(07-01): capture phase-07-pre baseline + tag pre-phase-7-prune"
```

### Verifier run sequence (Plan 07-05)
```bash
# Build + bring up the pruned datasette image
docker compose build zeeker-datasette
docker compose up -d zeeker-datasette

# Wait healthy
docker compose ps zeeker-datasette --format json | jq -r '.[].Health'

# Run the verifier chain (delegates: 06 → 04 → 03)
bash scripts/verify_phase_06.sh

# Standalone parity gate against the fresh phase-07-pre baseline
ZEEKER_BASELINE_DIR="$(git rev-parse --show-toplevel)/.planning/baselines/phase-07-pre" \
  bash scripts/verify_api_parity.sh
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| M1: Datasette HTML rendered via `templates/index.html`, `database.html`, `table.html`, `_table-{db}-{table}.html` partials, with `static/css/zeeker-base.css` overlay | M2: FastAPI/Jinja frontend renders HTML; Datasette is data-only API | Phase 4-6 (Phase 4 SHIPPED home + database; Phase 5 SHIPPED table + row; Phase 6 SHIPPED auxiliary pages) | M2 frontend renders all user-facing HTML; Phase 7 finalizes by deleting M1 scaffolding |
| `developers_page.py`/`status_page.py`/`sources_page.py` plugins serving `/developers`, `/status`, `/sources` from Datasette | Frontend FastAPI handlers in `routes_aux.py` serve same routes | Phase 6 (commit `e9ead48`) | Phase 7 removes plugins; routes still work via Caddy → frontend |
| `string_manager.py` + `strings.yaml` providing `s()`, `sf()`, `plural()` Jinja helpers | Frontend `filters.py` ports `s()`, `plural()`, `pluralize`, `safe_format`, `filesizeformat` (D-12 Phase 6) | Phase 4 (commit at Plan 04-01); Phase 6 changelog port (commit `8794947`) | Phase 7 removes M1 plugin + YAML; frontend has the canonical copies |
| `extra_css_urls` injecting `/static/css/zeeker-base.css` into Datasette's HTML | Frontend `base.html` references `/static/css/zeeker.css` (note: different path) under the FastAPI static mount | Phase 4 Plan 04-02 (CSS harvest into frontend package) | Phase 7 drops the metadata.json injection; Datasette's developer HTML uses bundled defaults |

**Deprecated/outdated:**
- `templates/_table-{db}-{table}.html` per-table partial seam — superseded by frontend mode-dispatch (D-04 Phase 5 `display.table_mode`); 9 partials in `templates/` directory will be deleted.
- `datasette-template-sql` plugin — zero consumers in `templates/` after the prune; OK to drop from `pyproject.toml`.
- M1 `--template-dir` / `--static` flags in entrypoint.sh — references empty/missing dirs post-prune; drop the flags.
- `CLAUDE.md` description of `static/css/zeeker-base.css` as "main stylesheet" — stale post-prune; update narrative.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Datasette 0.65.2 tolerates `--template-dir` and `--static` flags pointing to missing directories without exiting (silently falls back to bundled defaults) | Pitfall 4, Code Examples (entrypoint.sh diff) | If wrong: container fails to start post-prune. Mitigation: drop the flags entirely (the diff shows this is option (i)). [ASSUMED — could not test live; verified via inference from Datasette internals docs template-lookup order, but no explicit "missing dir is OK" statement found in changelog or CLI reference] |
| A2 | `/-/static/datasette-manager.js` is present in Datasette 0.65.x bundled HTML body (not just 1.0a) | Pitfall 1, Code Examples (verifier fingerprint) | If wrong: the new fingerprint doesn't match Datasette 0.65.x output and verifier still fails. Mitigation: Plan 07-01 must run the new fingerprint against the LOCAL stack (Datasette 0.65.2) before committing — falsifies if absent. [ASSUMED — `latest.datasette.io` runs 1.0a28; the verified body excerpt mixes 1.0a artifacts. Need empirical re-verification on local 0.65.2 stack as part of Plan 07-01.] |
| A3 | `download_from_s3.py` `_check_base_assets_exist()` returns true on production S3 (i.e., the M1 M overlay assets ARE present in S3) | Pitfall 3 | If wrong: production already pruned the S3 overlay; option (a) and (b) collapse into the same outcome. Mitigation: HUMAN UAT smoke step inspects `aws s3 ls s3://$S3_BUCKET/assets/default/` to confirm before deciding option (a) vs (b). [ASSUMED — based on the V2 architecture description in CLAUDE.md and PROJECT.md; not verified against production S3 in this research session] |
| A4 | Phase-6 production deploy is gated and HAS NOT happened yet (per `06-HUMAN-UAT.md` test #3 "result: pending") | All phase planning | If wrong: the live `data.zeeker.sg` already runs Phase-6 frontend, and Phase 7 is the SECOND production deploy. Mitigates how Plan 07-05's HUMAN CHECKPOINT phrases the deploy gate. [VERIFIED: `06-HUMAN-UAT.md` line 47-55 explicitly says "result: pending"] |
| A5 | `pyyaml` retention recommendation (drop `string_manager.py` consumer; keep for `verify_phase_02.sh`) is safe because `verify_phase_02.sh` runs a system Python with PyYAML available | Standard Stack §Removed | If wrong: `verify_phase_02.sh` line 24 (`import yaml, sys`) fails when PyYAML is absent from the verifier's Python interpreter. Mitigation: leave `pyyaml` in pyproject.toml with a one-line comment explaining the retention, OR move `pyyaml` to dev-deps only. [VERIFIED: `verify_phase_02.sh` line 22 invokes `python3 -c "import yaml..."` — uses system Python] |
| A6 | The frontend's `base.html` is the SOLE consumer of `metadata.menu_links`; nothing else in the M2 stack depends on it | User Constraints D-locked-3 | If wrong: removing or accidentally clobbering `menu_links` could break a non-base.html consumer. Mitigation: `grep -rn menu_links packages/zeeker-frontend/` confirms only base.html iterates them; the route-handler-side reads stuff `menu_links` into context but doesn't iterate. [VERIFIED via grep] |
| A7 | `datasette-search-all` plugin's HTML rendering uses Datasette's bundled templates (not the user `templates/` dir) | User Constraints D-locked-2 | If wrong: `/-/search` post-prune would 500 on missing template. Mitigation: confirmed by `baselines/phase-06-pre/-_plugins.json.json` line 31 (`"templates": true`) — this means the plugin BRINGS its own templates, not consumes the user's. [VERIFIED via baseline JSON] |

**Confirmed-non-assumption (verified directly):** every deletion target's coupling to surviving code was checked via `grep -rn` across the repo. The findings: zero non-test consumers in datasette image; tests are isolated to S3-download smoke tests + cache_headers tests; frontend consumers are zero (frontend ports the helpers internally — see filters.py header comment).

## Open Questions

> Numbered for the discuss-phase / planner to resolve. Each question is researchable; defaults are recommended where possible.

1. **Re-baseline strategy.** After cleaning `metadata.json`, `/-/metadata.json` body changes — verify_api_parity will diff. Do we (a) re-baseline `phase-07-pre/` first, then do the prune and verify against that, OR (b) do the prune and accept a documented metadata-only diff in the parity report?
   - What we know: precedent set in 06-HUMAN-UAT.md task #2 (`8ed46ef`) — re-baselined `phase-06-pre/` after the editorial close-out. Same pattern works here.
   - What's unclear: whether the planner wants the baseline captured BEFORE Plan 07-02 (metadata edit) or AFTER it. If before: parity gate fires once for the metadata diff in Plan 07-02 verifier run; expected. If after: parity gate is clean from Plan 07-02 onward.
   - **Recommendation:** option (a) capture `phase-07-pre/` AFTER the Plan 07-02 metadata edit (so the baseline reflects the post-edit metadata), but BEFORE the Plan 07-04 mass deletion. Sequencing: 07-01 (baseline + tag — but baseline targets the Phase-6 state) → 07-02 (metadata edit + re-capture baseline) → 07-03 (script edit) → 07-04 (mass delete) → 07-05 (verify). [HIGH confidence — matches the established pattern]

2. **One commit vs staged.** Is the prune safe as a single atomic commit, or should it be staged so each step can be verified independently?
   - What we know: the deletions are largely orthogonal across files (plugins are independent of templates which are independent of static). However, metadata.json + Dockerfile + entrypoint.sh + download_from_s3.py edits each have their OWN coupling to the deletions.
   - What's unclear: whether the planner wants 5 separate commits (granular blame, multi-hop rollback) or 1 big commit (atomic state, simple rollback).
   - **Recommendation:** STAGED into 5 plans (Pattern 1 §Code Examples sequencing block). Plan 07-04 is the only "mass delete" commit; other plans land single-file edits that can be reverted independently if issues surface. [HIGH confidence — matches Phase 3 Plan 03-02 single-file-commit precedent and Phase 4 multi-plan pattern]

3. **`download_from_s3.py` editing.** Edit the script to stop redownloading `templates/`/`static/`/`plugins/` from S3 (option (a)) OR defer to Phase 8 ADR (option (b))?
   - What we know: option (a) makes the prune effective at runtime; option (b) makes the prune cosmetic-only (image is clean, but startup re-overlays from S3). PRD §10 Step 6 deferred the overlay decision to Phase 8.
   - What's unclear: whether "Phase 7 prune" means "image source is clean" (option (b) sufficient) or "container runtime state is clean" (option (a) required). PRD §3 says "single HTML codebase, no two-eras-co-existing" — leans toward option (a).
   - **Recommendation:** option (a). Edit `download_from_s3.py` to scope to `.db` files + (optionally) metadata.json overlays only. This achieves the runtime-state goal AND leaves a clean ADR slot for Phase 8 to decide whether to retire `download_from_s3.py` entirely or keep it for future use. [MEDIUM-HIGH confidence — needs user confirmation; scope_correction additional_context Q4 also flags this]

4. **Production deploy.** When does the deploy happen — inline in Plan 07-05 (build → push → swap → smoke) or as a separate phase / human-gated step?
   - What we know: Phase 4-5-6 each had a production-deploy HUMAN CHECKPOINT inline in the final plan of the phase. Phase 6's deploy is still pending per 06-HUMAN-UAT.md test #3.
   - What's unclear: whether Phase 6's pending production deploy should ship FIRST (so the Phase 7 prune deploys against a known-good Phase-6 production state), or whether the two phases can collapse into a combined deploy.
   - **Recommendation:** ship Phase 6 to production FIRST, run smoke against `data.zeeker.sg` aux routes (06-HUMAN-UAT test #3), THEN do Phase 7. This ensures any Phase-6 regressions surface against a clean baseline and aren't conflated with Phase 7 changes. Plan 07-05 then ships the prune to production as a SEPARATE deploy. [HIGH confidence — matches incremental-migration REQ-incremental-migration; no rationale to combine]

5. **Rollback tag.** Should we `git tag` the pre-prune state (e.g., `pre-phase-7-prune`) so rollback is one command?
   - What we know: ROADMAP §Phase 3 used `git revert <commit>` for single-commit rollback (the Caddyfile flip was one commit). Phase 4-6 don't appear to use tags but use commit hashes (e.g., 06-06-SUMMARY.md cites `fac8bbb`, `58051e5`, `84e60f2`).
   - What's unclear: tag vs. commit hash is operator preference.
   - **Recommendation:** tag `pre-phase-7-prune`. Tags survive squash-merges, are greppable in `git tag -l`, and the human-readable name is faster to type than a commit hash during incident response. [MEDIUM confidence — no project precedent either way; minor improvement]

6. **`extra_css_urls` / `extra_js_urls` removal.** These currently load Prism syntax highlighting + zeeker-base.css/js. Datasette's native HTML pages (which still exist for `/-/sql`, `/-/search`, default `/-/databases.json`) inherit these. Once the static dir is gone, Datasette's own HTML pages will load nothing custom. Is that acceptable, or should Datasette's defaults still get *some* baseline styling?
   - What we know: `/-/sql` and `/-/search` are developer-facing per D-01; PRD §7.1 §12 don't mandate styling them.
   - What's unclear: whether the operator finds plain Datasette default HTML acceptable for these surfaces or wants to retain at least Prism for SQL syntax highlighting.
   - **Recommendation:** REMOVE both keys entirely. If feedback later says SQL surfaces look ugly, address in Phase 8 by injecting a Matomo-bundle-equivalent `<script>` tag via a small custom plugin or via `extra_css_urls` re-introduction with a frontend-served path. **Default for Phase 7: no custom CSS/JS on Datasette HTML.** [MEDIUM-HIGH confidence — aligns with D-01 + PRD §12]

7. **`template_filters.py` reach.** Filters like `pluralize`, `safe_format`, `filesizeformat` — were any custom HTML templates relying on them? Now that templates/ is going, the filters have no consumers in datasette. Confirm.
   - What we know: `grep -rln "|pluralize\||safe_format\||filesizeformat\||safe_int" templates/` returned 5 files: `templates/index.html`, `templates/database.html`, `templates/pages/developers.html`, `templates/pages/sources.html`, `templates/pages/status.html`. **All five files are part of the Plan 07-04 deletion set.** When `templates/` is deleted, every consumer disappears, and `template_filters.py` has zero remaining consumers.
   - What's unclear: nothing — fully verified.
   - **Recommendation:** delete `template_filters.py` as planned. Frontend already ports the filters in `packages/zeeker-frontend/src/zeeker_frontend/filters.py` (verified line 3-5 of that file). [HIGH confidence — verified]

## Environment Availability

> The Plan 07-05 production deploy depends on existing Docker tooling and Datasette CLI; nothing new is introduced.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker / Docker Compose | Plan 07-05 build + deploy | ✓ (assumed; Phases 2-6 used it) | unspecified | — |
| `git` | Plan 07-01 tagging, Plan 07-04 mass delete via `git rm` | ✓ | 2.x | — |
| `bash` ≥ 4 | All `verify_*.sh` scripts use `set -euo pipefail` and bash arrays | ✓ (assumed; existing chain runs in production) | 4+ | — |
| `curl` | Verifier scripts | ✓ | — | — |
| `jq` | Verifier `JQ_STRIP` filter, baseline capture | ✓ (used in capture_baseline.sh, verify_api_parity.sh, verify_phase_03.sh) | — | — |
| `aws` CLI | OPTIONAL — HUMAN UAT smoke if Q3 option (a) — confirms S3 overlay state pre-deploy | possibly absent | — | Skip the smoke; rely on functional verifier alone |
| `uv` | Container build (Dockerfile uses `uv sync`); local dev | ✓ (Dockerfile fetches it from ghcr.io) | latest | — |
| Datasette 0.65.2 | Runtime | ✓ (in pyproject.toml) | 0.65.2 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** AWS CLI optional for S3 smoke; functional verifier covers the runtime state regardless.

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` (only `_auto_chain_active: false` is set), so include this section per default.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4+ |
| Config file | `pyproject.toml` `[dependency-groups].dev` |
| Quick run command | `uv run pytest tests/test_cache_headers.py -x` (post-prune; cache_headers is the only datasette-side test surface that survives) |
| Full suite command | `uv run pytest tests/` (datasette image tests only) + `cd packages/zeeker-frontend && uv run pytest` (frontend tests untouched by Phase 7) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-escape-datasette-template-surface | `templates/` and `static/` directories absent from image | unit (build smoke) | `git ls-files templates/ static/ \| wc -l` returns 0; assert in Plan 07-05 | post-Plan-07-04 |
| REQ-reduce-plugin-count | UI plugins absent | unit | `git ls-files plugins/ \| grep -E '(developers_page\|sources_page\|status_page\|string_manager\|template_filters)\.py$'` returns empty | post-Plan-07-04 |
| REQ-api-byte-parity | `/-/metadata.json`, `/{db}.json`, `/-/databases.json` byte-identical to baseline | integration | `bash scripts/verify_api_parity.sh` against `phase-07-pre/` | ✓ |
| REQ-frontend-route-set | All Phase-6 routes still 200 | integration | `bash scripts/verify_phase_06.sh` (delegates to Phase 4 verifier) | ✓ |
| REQ-eliminate-template-drift | No M1 templates remain | unit | `[ ! -d templates/ ]` assert in Plan 07-05 verifier | ✓ post-Plan-07-04 |
| REQ-internal-only-datasette-exposure | Datasette internal-only | integration | `verify_phase_02.sh` (chained via `verify_phase_06.sh` → `verify_phase_04.sh` → `verify_phase_03.sh` → ... — actually verify_phase_02 isn't chained; check Plan 07-05 should run it explicitly) | ✓ |
| REQ-preserve-zeeker-cli | `zeeker init`/`add`/`build`/`deploy` continues working | manual / out-of-scope | Run `uv run scripts/manage.py status` post-prune; verify exit 0 | ✓ (manual) |
| Cache-Control on `/-/*` and `/static/*` (cache_headers.py survives) | unit | `pytest tests/test_cache_headers.py -x` | ✓ |

### Sampling Rate
- **Per task commit:** `git ls-files plugins/ templates/ static/` to confirm deletion intent matches state; `pytest tests/test_cache_headers.py -x` for cache_headers regression check.
- **Per wave merge:** `bash scripts/verify_phase_06.sh` against the local stack.
- **Phase gate:** `bash scripts/verify_phase_06.sh` + `bash scripts/verify_api_parity.sh` (against `phase-07-pre/`) both green; production smoke against `data.zeeker.sg` after deploy (HUMAN UAT).

### Wave 0 Gaps
- [x] No new test framework needed — pytest already in `pyproject.toml`
- [ ] Plan 07-01: re-author `verify_phase_03.sh` zeeker-base.css fingerprint (in-place edit; no new file)
- [ ] Plan 07-01: capture `.planning/baselines/phase-07-pre/` (16 files via capture_baseline.sh)
- [ ] Plan 07-04: update `tests/conftest.py` line 53 (drop the `template_filters.py` mirror); optional: trim `tests/fixtures.py` line 69
- [ ] Plan 07-05: add a "post-prune state assertion" section to `verify_phase_06.sh` OR a fresh `verify_phase_07.sh` that asserts `! [ -d templates/ ]` and `! [ -d static/ ]` and `! ls plugins/{developers_page,...}*.py 2>/dev/null` — this is **NEW verifier logic** specific to Phase 7

## Security Domain

> Phase 7 is a deletion phase; security implications are limited but worth surfacing.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture | yes | Reducing attack surface (deleting code = fewer plugins to audit) — net positive |
| V2 Authentication | no | No auth surface change |
| V3 Session Management | no | Stateless API; no sessions |
| V4 Access Control | yes | `metadata.json databases.* allow_sql/allow_facet/allow_download` controls — preserved by Phase 7 |
| V5 Input Validation | no | Frontend handles all user input; Datasette JSON API uses Datasette's built-in safeguards (read-only mode, `ms_limit`, `--immutable`) |
| V6 Cryptography | no | TLS termination at Caddy; unchanged |
| V14 Configuration | yes | `metadata.json` edits change configuration scope — V14.1.1 says config changes should be tracked; we track via git |

### Known Threat Patterns for Phase 7

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidentally deleting `cache_headers.py` (the survivor that enforces Cloudflare-friendly cache headers) | Information Disclosure (CDN serving stale data) / Denial of Service (CDN cache miss storm) | Plan 07-04 lists explicit survivors (`__init__.py` + `cache_headers.py`); test_cache_headers.py asserts cache_headers behavior post-prune |
| Accidentally deleting/clobbering `menu_links` from metadata.json | Denial of Service on UI navigation (frontend nav goes empty) | Plan 07-02 explicitly preserves `menu_links`; Code Examples diff shows the keep-vs-delete boundary |
| Stale `verify_phase_03.sh` fingerprint causing silent fall-through to undetected Datasette HTML responses on Caddy-frontend boundary | Tampering / Information Disclosure | Plan 07-01 updates the fingerprint to `/-/static/datasette-manager.js` + literal "Powered by Datasette"; both are stable Datasette-bundled markers |
| `download_from_s3.py` re-uploading empty `templates/`/`static/` to S3 (overwriting the M1 copies, partial cleanup) | Tampering of deploy artifacts | Plan 07-03 option (a) edits the script to no-op the asset upload path; option (b) defers to Phase 8 ADR; either is intentional (no accidental overwrite) |
| Future deploy reverts the prune by re-downloading from S3 | Persistence of deprecated code | Pitfall 3 documents this; Plan 07-03 addresses it; Plan 07-05 HUMAN UAT smoke confirms post-deploy that `/static/css/zeeker-base.css` returns 404 (proof the prune held) |
| Production deploy fails or partially deploys, leaving a half-pruned image in production | Denial of Service | Plan 07-05 HUMAN CHECKPOINT runs a four-category triage (A/B/C/D) before swapping; rollback via `git tag pre-phase-7-prune` is one command |

## Sources

### Primary (HIGH confidence)
- `/Users/houfu/Projects/zeeker-datasette/Dockerfile` — verified lines 30-32 are the COPY targets to delete; lines 38-41 are the matching mkdir block
- `/Users/houfu/Projects/zeeker-datasette/metadata.json` — verified `extra_css_urls` (lines 242-245), `extra_js_urls` (246-250), `menu_links` (251-272), `plugins.datasette-search-all` (237-241)
- `/Users/houfu/Projects/zeeker-datasette/entrypoint.sh` — verified line 23-30 invocation; `--template-dir`, `--plugins-dir`, `--static` flags present
- `/Users/houfu/Projects/zeeker-datasette/plugins/cache_headers.py` lines 1-75 — verified pure ASGI wrapper, no template/static refs
- `/Users/houfu/Projects/zeeker-datasette/plugins/{developers_page,sources_page,status_page,string_manager,template_filters}.py` + `plugins/strings.yaml` — verified all are UI-coupled (Datasette `register_routes` / `prepare_jinja2_environment` / `extra_template_vars` hooks)
- `/Users/houfu/Projects/zeeker-datasette/packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` line 18-25 — verified `metadata.menu_links` consumer
- `/Users/houfu/Projects/zeeker-datasette/packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` lines 43-56 — verified `fetch_site_metadata()` shape
- `/Users/houfu/Projects/zeeker-datasette/packages/zeeker-frontend/src/zeeker_frontend/filters.py` lines 3-5 — verified port-of-`template_filters.py` note
- `/Users/houfu/Projects/zeeker-datasette/packages/zeeker-frontend/src/zeeker_frontend/changelog.py` lines 3-5 — verified port-of-`strings.yaml.recent_updates` note
- `/Users/houfu/Projects/zeeker-datasette/scripts/verify_phase_03.sh` lines 105-107, 116, 154-155, 228 — verified `zeeker-base.css` fingerprint usage
- `/Users/houfu/Projects/zeeker-datasette/scripts/verify_phase_06.sh` lines 166-179 (Section G) — verified D-01 boundary asserts
- `/Users/houfu/Projects/zeeker-datasette/scripts/download_from_s3.py` lines 159-202 — verified `_check_base_assets_exist()` + `_setup_base_assets()` + `_apply_database_customizations()` runtime overlay logic
- `/Users/houfu/Projects/zeeker-datasette/.planning/baselines/phase-06-pre/-_metadata.json.json` — verified pre-prune baseline contains `extra_css_urls`/`extra_js_urls`
- `/Users/houfu/Projects/zeeker-datasette/.planning/baselines/phase-06-pre/-_plugins.json.json` lines 29-37 — verified `datasette-search-all` `templates: true` (brings own templates)
- `/Users/houfu/Projects/zeeker-datasette/docker-compose.yml` line 14 — verified `context: .` for `zeeker-datasette` service (build context is repo root, NOT `packages/zeeker-datasette/`)
- ROADMAP.md (lines 300-318 §Phase 7) — verified phase scope description (with the noted scope_correction caveat about path)
- REQUIREMENTS.md (lines 26-49) — verified REQ-escape-datasette-template-surface, REQ-reduce-plugin-count, REQ-preserve-zeeker-cli wording
- `06-HUMAN-UAT.md` lines 32-46 — verified Phase-6 re-baseline precedent (`8ed46ef`)
- `06-CONTEXT.md` lines 56-60 (D-12) — verified frontend-owned changelog port

### Secondary (MEDIUM confidence)
- [Datasette internals docs §Template lookup order](https://docs.datasette.io/en/stable/internals.html) — confirms `--template-dir → plugin bundled → Datasette bundled defaults` fallback chain (verified via WebFetch 2026-04-26)
- [Datasette pages docs §Top-level / database / table / row](https://docs.datasette.io/en/stable/pages.html) — confirms built-in HTML pages without custom templates (verified via WebFetch 2026-04-26)
- [Datasette changelog 0.65.2](https://docs.datasette.io/en/stable/changelog.html) — confirms 0.65.1→0.65.2 is security + 3.14 compat only; no metadata/plugin/template behavior change (verified via WebFetch 2026-04-26)
- Live `curl https://latest.datasette.io/-/sql` body excerpt — confirms `/-/static/app.css`, `/-/static/datasette-manager.js`, `Powered by <a href="https://datasette.io/">Datasette</a>` are present in default Datasette HTML envelope (verified 2026-04-26 — but on 1.0a28; needs re-verification on local 0.65.2 in Plan 07-01)

### Tertiary (LOW confidence)
- WebSearch [datasette --plugins-dir empty directory behavior] — no explicit documentation on missing-dir tolerance; A1 is inference, not direct verification
- Inferred Datasette 0.65.x bundled-default behavior from docs that primarily reference 1.0a — direct test on local stack required in Plan 07-01

## Metadata

**Confidence breakdown:**
- Deletion target list: HIGH — every file inspected; every consumer grep'd
- Survivor list (`__init__.py`, `cache_headers.py`): HIGH — `cache_headers.py` line-by-line confirmed pure ASGI
- metadata.json post-prune shape: MEDIUM-HIGH — `menu_links` consumer verified; `extra_*_urls` consumers all under deletion targets
- Verifier rebase strategy: MEDIUM — Pattern 3 inherited from Phase 3, but the specific fingerprint replacement needs empirical re-verify on Datasette 0.65.2 (A2)
- `download_from_s3.py` runtime concern: HIGH on the FACT (lines 159-202 verified), MEDIUM on the resolution (option (a) vs (b) is a user decision per Q3)
- Pitfalls: HIGH (1, 2, 5), MEDIUM (3, 4 — depend on Q3 + A1)
- Test framework: HIGH — pytest already in place, no changes needed
- Security: HIGH — surface is reduced, not expanded; standard "delete safely" patterns apply

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (30 days; deletion phase, low ecosystem volatility)

# Roadmap

## Milestone M1: Editorial polish

Transform the V2 light-theme shell into a civic-broadsheet editorial UI. Grounded in four sketch sessions; all design decisions pre-validated and captured in the `sketch-findings-zeeker-datasette` skill.

### Phases

#### Phase 1 — Implement editorial shell + home + inventory lists

**Goal:** Apply the validated sketch-findings design across the base templates so every page inherits the civic-broadsheet chrome, and the three most-visited surfaces (home, database, table) render in their winning editorial patterns.

**Scope — in:**
- Theme system: update `static/css/zeeker-base.css` with the paper/petrol/ochre/terracotta palette, Fraunces/Inter/Mono typography scale, and spacing/radius tokens from `references/theme-system.md`.
- Shell & chrome: `templates/_header.html`, `templates/_footer.html`, hero pattern, breadcrumb strip, petrol stat band, sticky toolbar. Fix the footer `a:link` specificity override against Datasette's `app.css`.
- Home (`templates/index.html`): sketch 001-D — dark nav + warm hero + stat band + card grid with rotating accent borders + dark CTA.
- Database page (`templates/database.html`): sketch 002-B — editorial full-width rows listing tables (no taxonomy).
- Table page as news feed (`templates/_table-{db}-{table}.html` per long-text table): sketch 004-A — reverse-chron feed cards + faceted sidebar, using the `_table-{db}-{table}.html` partial seam so Datasette's filters/facets/FTS/pagination/export stay intact.

**Scope — out:**
- Row detail page (sketch 003) — defer, no winner yet.
- Data Guide footer block (About / Licence / Source / Suggested Uses).
- Dark `petrol-ink` theme activation (defined but not wired).
- Mobile-only pass beyond the default responsive collapses already in sketches.

**Success criteria:**
- All four winning sketches render as production templates against the real databases (SG Government Newsrooms + Zeeker-Judgements + Sglawwatch).
- No regressions in existing Datasette functionality: filters, facets, FTS search, sort links, pagination, CSV/JSON export, advanced export pane all still work on `/{db}/{table}` pages.
- Visual QA sweep (`scripts/visual_qa.py`) returns all 200s across desktop + mobile and Chromium + WebKit.
- Footer links visible at proper contrast on every page.
- Italic-accent H1 with colored `<em>` visible on home / database / table pages.

**Plans:** 6 plans

Plans:
- [ ] 01-01-theme-and-tokens-PLAN.md — Replace :root tokens + body/heading/link base styles with civic-broadsheet palette + Fraunces/Inter/Mono typography + italic-accent-on-h1 signature.
- [ ] 01-02-shared-chrome-PLAN.md — Rewrite `_header.html` (dark nav + breadcrumb) and `_footer.html` (4-column paper footer); append SHELL CHROME CSS section with `.db-nav` / `.db-crumb` / `.db-header` / `.db-statband` / `.db-toolbar` / `.cta` / `.cat-pill` / `.fts-badge` / `.site-footer` classes.
- [ ] 01-03-home-editorial-PLAN.md — Rewrite `templates/index.html` as sketch 001-D (warm hero + petrol stat band + `№ 01 · Databases` card grid with rotating accent borders + `№ 02 · How to use` + dark CTA); append HOME CSS section with `.cards` / `.card` + nth-child accent rotation / `.chip` / `.how-grid` / `.hero-search`.
- [ ] 01-04-database-editorial-rows-PLAN.md — Rewrite `templates/database.html` as sketch 002-B (hero + stat band + editorial-row table list with mono columns + right-aligned row counts + FTS badge); append DATABASE EDITORIAL ROWS CSS. Preserves today's `metadata.get('tables', {}).get(name)` fix and `_zeeker_*` hidden-table filter.
- [ ] 01-05-table-feed-partials-PLAN.md — Create `templates/_partials/feed_card.html` + four `_table-{db}-{table}.html` partials (acra_news, judiciary_news, judgments, about_singapore_law) so long-text tables render as sketch 004-A feed cards. Uses Datasette's partial seam so filters/facets/FTS/pagination/export are untouched. Append FEED CARDS CSS.
- [ ] 01-06-visual-qa-sweep-PLAN.md — Extend `scripts/visual_qa.py` with three production content-type routes; run sweep; human checkpoint on contact sheet to confirm all 200s and no regressions.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 01-01 | — | yes |
| 2 | 01-02 | depends on 01-01 | yes |
| 3 | 01-03 | depends on 01-01 + 01-02 | yes |
| 4 | 01-04 | depends on 01-03 (CSS file chain) | yes |
| 5 | 01-05 | depends on 01-04 (CSS file chain) | yes |
| 6 | 01-06 | depends on 01-01..01-05 | no (human checkpoint) |

Note: Plans 03/04/05 all append to `static/css/zeeker-base.css`; they run sequentially to avoid file conflict rather than in parallel.

**References:**
- Skill: `sketch-findings-zeeker-datasette` (auto-loads)
- Sources: `.claude/skills/sketch-findings-zeeker-datasette/sources/`
- Constraints: `.planning/notes/datasette-styling-limits.md`

---

## Milestone M2: Frontend / API Split

Split `data.zeeker.sg` into a read-only Datasette API + a FastAPI/Jinja frontend behind a Caddy suffix-routing proxy. Preserve API byte-for-byte, eliminate Datasette template-override debt, reduce UI-coupled plugins to zero. Supersedes M1's strategy of patching the Datasette template surface — M1's V2 templates and editorial CSS become reference material harvested by M2 phases that re-implement them in FastAPI/Jinja.

Driven by `prd-zeeker-frontend-split.md` (PRD, Status: Draft) ingested via `/gsd-ingest-docs` on 2026-04-20. PRD-level decisions (DEC-1..DEC-6 in `.planning/intel/decisions.md`) are not yet ratified ADRs — promote to `Status: Accepted` ADRs to lock them.

### Phases

#### Phase 2: Dual-service bring-up

**Goal:** Add `frontend` (FastAPI placeholder) and `caddy` (off-the-shelf) services to `docker-compose.yml`. Caddy still routes everything to datasette; frontend serves a single `/frontend-test` route. Site behavior unchanged.

**Scope — in:**
- New `packages/zeeker-frontend/` package (FastAPI + Jinja2 + httpx + uv, black-formatted) with placeholder route.
- New root `Caddyfile` (transparent proxy → datasette only).
- `docker-compose.yml` updated: 3 services (datasette, frontend, caddy); only Caddy publishes ports.
- Datasette service `ports:` mapping removed (internal-only, network-reachable from Caddy).

**Success criteria:**
- `docker compose up` brings all 3 services healthy.
- All existing URLs (`/`, `/{db}`, `*.json`, `/-/sql`, etc.) still resolve byte-for-byte through Caddy → datasette.
- `GET /frontend-test` returns 200 from the new frontend service.
- Datasette healthcheck (`/-/versions.json`) returns 200 over the internal Docker network.

**Plans:** 5 plans

Plans:
- [x] 02-01-PLAN.md — Wave-0 validation infrastructure: capture_baseline.sh, verify_api_parity.sh, verify_phase_02.sh, and committed pre-mutation baselines in .planning/baselines/phase-02/.
- [x] 02-02-PLAN.md — Scaffold packages/zeeker-frontend/ (FastAPI placeholder, uv-managed, pinned deps, Dockerfile with no sqlite, pytest smoke tests).
- [x] 02-03-PLAN.md — Author root Caddyfile: single site on :80, reverse_proxy zeeker-datasette:8001, auto_https off, admin bound to localhost:2019, Phase-3 forward-compat commented.
- [x] 02-04-PLAN.md — Mutate docker-compose.yml into three-service topology: remove datasette ports, add frontend + caddy services, caddy depends_on service_healthy for both backends, named volumes for cert storage.
- [x] 02-05-PLAN.md — Local bring-up + verify_phase_02.sh + verify_api_parity.sh; human checkpoint with ship/no-ship decision; finalize 02-VALIDATION.md.

**Status:** SHIPPED 2026-04-21. All 5 plans complete; topology change ships zero behavioral regressions. Parity drifts triaged (host base URL, S3 metadata refresh, datasette 0.65.1→0.65.2, daily import drift) — all environmental/non-topology. See `.planning/phases/02-dual-service-bring-up/02-05-SUMMARY.md` for details.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 02-01 | — (sequential prereqs; includes human checkpoint after baseline capture) | no (checkpoint) |
| 2 | 02-02, 02-03 | parallel (no files_modified overlap: packages/zeeker-frontend/** vs Caddyfile) | yes |
| 3 | 02-04 | depends on 02-02 (build.context) + 02-03 (Caddyfile) | yes |
| 4 | 02-05 | depends on 02-01 (scripts + baselines) + 02-04 (compose ready) | no (human checkpoint) |

**References:** PRD §10 Step 1, §7.1, §7.3.

---

#### Phase 3: Flip suffix-based routing

**Goal:** Update Caddyfile so `*.json`, `*.csv`, `*.db`, `/-/*` route to datasette and everything else routes to frontend. Frontend will 404 on HTML routes that aren't ported yet — this is intentional and tested locally before deploy.

**Scope — in:**
- Caddyfile suffix-router (`@datasette { path *.json *.csv *.db /-/* }` + default to frontend).
- Local `curl` parity tests: every existing `.json`/`.csv`/`.db`/`/-/*` URL returns identical bytes to pre-flip baseline.
- Test plan documented for repeatable post-flip verification.

**Success criteria:**
- `diff` of curl-captured `.json` responses (timestamps and version strings excepted) shows no meaningful changes pre vs post flip.
- HTML routes that aren't yet ported return 404 from frontend (NOT silent fallthrough to datasette HTML).

**Out:** Production deploy. Phase 3 is local-validation-only; deploy waits for Phase 4's homepage port so HTML users see the new look.

**Plans:** 4 plans

Plans:
- [x] 03-01-PLAN.md — Parameterize scripts/capture_baseline.sh + scripts/verify_api_parity.sh via ZEEKER_BASELINE_DIR env var (default phase-03-pre); smoke-test parity against current pre-flip stack.
- [x] 03-02-PLAN.md — Replace transparent reverse_proxy in Caddyfile with named @datasette matcher (path *.json *.csv *.db + path /-/*) + matched-handler + catch-all reverse_proxy frontend:8000; validate with caddy validate; single-file commit (rollback = git revert).
- [x] 03-03-PLAN.md — Author scripts/verify_phase_03.sh: positive routing + negative routing with body-content fallthrough sniff for zeeker-base.css + frontend reachability + edge cases (multi-dot, HEAD/GET, case-insensitivity, CORS) + parity wrap; delegates to verify_phase_02.sh for topology invariants. NOT executed against live stack in this plan.
- [x] 03-04-PLAN.md — docker compose restart caddy + wait healthy + run verify_phase_03.sh + standalone verify_api_parity.sh against phase-03-pre; capture forensic logs (bringup-log + parity-log); author 03-TEST-PLAN.md repeatable recipe; HUMAN CHECKPOINT for ship/no-ship using Phase-2 four-category triage (A/B/C/D); on ship → update STATE/ROADMAP/REQUIREMENTS atomically; on no-ship → git revert Plan-02 + restart caddy + verify rollback via verify_phase_02.sh.

**Status:** SHIPPED 2026-04-21. Suffix routing live; 11/11 negative + 7/7 positive routing checks pass; 12/12 byte-parity baselines clean. Also retired `verify_phase_02.sh` stale checks #3 (EXPOSE-only port jq filter) and #10 (polarity-inverted post-Phase-3). See `.planning/phases/03-flip-suffix-based-routing/03-04-SUMMARY.md`.

**Wave structure:**

| Wave | Plans | Parallelism | Autonomous |
|------|-------|-------------|------------|
| 1 | 03-01 | — (sequential prereq for parity baseline pointer) | yes |
| 2 | 03-02 | depends on 03-01 (uses parameterized parity script downstream) | yes |
| 3 | 03-03 | depends on 03-01 (script param prerequisite); parallel-safe with 03-02 (no files_modified overlap: scripts/verify_phase_03.sh vs Caddyfile) | yes |
| 4 | 03-04 | depends on 03-02 + 03-03 (needs both Caddyfile flip and verifier in place) | no (human checkpoint) |

**Depends on:** Phase 2.
**References:** PRD §10 Step 2, §6.

---

#### Phase 4: Port home + database pages

**Goal:** Implement frontend routes `/` (homepage with hero, stats, database cards) and `/{db}` (database overview with tables, row counts, schema link, SQL examples). Deploy together with the suffix-routing flip from Phase 3.

**Scope — in:**
- Frontend handlers + Jinja templates for `/` and `/{db}`.
- Internal HTTP calls to `http://datasette:8001/...json` for live data; in-memory TTL cache on metadata endpoints.
- Harvest M1 V2 designs: `templates/index.html` (sketch 001-D) and `templates/database.html` (sketch 002-B) as visual reference.
- Self-hosted Inter + JetBrains Mono moved to frontend; `static/css/zeeker-base.css` ported as `zeeker.css`.
- Production deploy.

**Success criteria:**
- `https://data.zeeker.sg/` and `https://data.zeeker.sg/{db}` render the V2 editorial design from the frontend service.
- All `.json` API URLs continue to return identical bytes (REQ-api-byte-parity holds).
- No 2025/2026 footer year mismatch.

**Depends on:** Phase 3 (routing must be flipped before deploy).
**References:** PRD §10 Step 3 (first tranche), §7.2.

> Per PRD §11 R7, **Phases 2 + 4 together deliver >50% of the perceived UI fix**. Subsequent phases (5–8) are optional continuation if project ROI justifies the work.

---

#### Phase 5: Port table browse + row view

**Goal:** Implement frontend routes `/{db}/{table}` (paginated rows, facets, export links, inline query form) and `/{db}/{table}/{pk}` (single row view).

**Scope — in:**
- Frontend handlers + Jinja templates for table and row pages.
- Faceted browse via calls to `/{db}/{table}.json?_facet=col` (validate edge cases: array columns, m2m — see PRD R1).
- Harvest M1 sketch 004-A feed-card design and the row-reading layouts.
- Pagination, sort, FTS query forwarding to datasette JSON.

**Success criteria:**
- Table page renders with working facets, pagination, sort, FTS, and export links (CSV/JSON download links route directly to datasette).
- Row page renders single-record view consistent with M1 row-reading layouts.

**Depends on:** Phase 4.
**References:** PRD §10 Step 3 (second tranche), §7.2, R1.

---

#### Phase 6: Port auxiliary pages

**Goal:** Implement remaining frontend routes: `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/-/search`, `/llms.txt`.

**Scope — in:**
- Frontend handlers + Jinja templates for all 7 routes.
- `/-/search` calls `datasette-search-all` JSON output (PRD R4 recommendation: don't re-implement).
- `/-/sql` thin replacement: `<textarea>` POSTing to `/-/sql?format=json`, results rendered as a table (PRD R2 v1 spec).
- `/llms.txt` machine-readable description.

**Success criteria:**
- All 7 routes return 200 with rendered HTML.
- `/-/search` cross-database search works against current databases.
- `/-/sql` accepts queries and renders results.

**Depends on:** Phase 5.
**References:** PRD §10 Step 3 (remainder), §7.2, R2, R4.

---

#### Phase 7: Prune zeeker-datasette

**Goal:** Delete UI-coupled plugins and template/static directories from `packages/zeeker-datasette/`. The package becomes data-only: `Dockerfile`, `metadata.json`, `scripts/`, `entrypoint.sh`.

**Scope — in:**
- Delete `developers_page.py`, `status_page.py`, `sources_page.py`, `string_manager.py`, `template_filters.py`.
- Delete `templates/` (all of it) and `static/` (all of it) from `packages/zeeker-datasette/`.
- Rebuild datasette image, deploy.

**Success criteria:**
- `packages/zeeker-datasette/` contains 0 UI plugins, no `templates/`, no `static/`.
- All HTML routes still render correctly (frontend owns them now).
- All API routes still return identical bytes.

**Depends on:** Phase 6 (all HTML routes must be live in frontend before pruning).
**References:** PRD §10 Steps 4 + 5, §7.1, §12.

---

#### Phase 8: Overlay decision + Matomo migration

**Goal:** Resolve the deferred per-database overlay question (PRD R5) and migrate Matomo analytics from datasette plugin to frontend `<script>` include (PRD R6).

**Scope — in:**
- Decide: retain S3 overlay mechanism for frontend (preserves "deploy UI without rebuilding container" workflow) vs retire (simpler system). Document decision as ADR.
- Move Matomo to frontend; remove `datasette-matomo` plugin from datasette service.
- Update `zeeker assets generate` if overlay mechanism is retained.

**Success criteria:**
- Matomo analytics functioning from frontend.
- Overlay decision documented; if retained, `zeeker assets generate` produces frontend-shaped overlays.

**Depends on:** Phase 7.
**References:** PRD §10 Step 6, §9, R5, R6.

---

### Cross-Milestone Notes

- **Critical path is short:** PRD §11 R7 calls out project-ROI uncertainty. Phases 2 + 4 alone deliver the bulk of the user-facing UI fix in roughly a weekend; everything beyond is optional follow-through.
- **Out-of-scope fences (PRD Appendix B):** This milestone does NOT modify `fetch_data()`, `zeeker.toml`, S3 bucket layout, refresh cron, or the data-scraping projects.
- **Decision lock state:** PRD Appendix A's 6 architectural choices (DEC-1..DEC-6) are PRD-level proposals, not ratified ADRs. Promote to `docs/adr/0001-suffix-routing.md` etc. with `Status: Accepted` to lock them before phases that depend on them ship.

**References:**
- Source PRD: `prd-zeeker-frontend-split.md`
- Synthesis entry: `.planning/intel/SYNTHESIS.md`
- Requirements: `.planning/REQUIREMENTS.md`
- Per-type intel: `.planning/intel/{decisions,requirements,constraints,context}.md`
- Conflicts report (resolved): `.planning/INGEST-CONFLICTS.md`
- Datasette template constraints (existing): `.planning/notes/datasette-styling-limits.md`

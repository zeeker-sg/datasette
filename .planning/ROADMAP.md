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

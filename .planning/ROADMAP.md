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

**References:**
- Skill: `sketch-findings-zeeker-datasette` (auto-loads)
- Sources: `.claude/skills/sketch-findings-zeeker-datasette/sources/`
- Constraints: `.planning/notes/datasette-styling-limits.md`

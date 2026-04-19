---
phase: 01-editorial-shell-home-inventory
plan: 02
subsystem: ui
tags:
  - shell
  - chrome
  - header
  - footer
  - css
  - nav
  - breadcrumb
  - hero
  - statband
  - toolbar
  - cta
  - cat-pill
  - site-footer

# Dependency graph
requires:
  - 01-01-theme-and-tokens
provides:
  - "Dark editorial nav (.db-nav) with ochre logo (CSS-uppercased, not Jinja) + right-aligned 4-link menu"
  - "Breadcrumb strip (.db-crumb) rendered below nav when `breadcrumbs` is set — mono/uppercase, petrol current"
  - "Asymmetric hero primitives (.db-header + .db-header-grid + .db-header .meta-col) reusable on home / database / table"
  - "Petrol stat band (.db-statband) with ochre stat numbers — 4-col on desktop, 2-col under 960px"
  - "Sticky sub-toolbar (.db-toolbar + .db-toolbar-search + .view-toggle) ready for database-page consumption in Plan 04"
  - "Dark CTA block (.cta + .btn-primary + .btn-ghost) ready for home-page consumption in Plan 03"
  - "Category pills (.cat-pill.press-release / .speech / .announcement / .newsletter) ready for feed cards in Plan 05"
  - "FTS badge (.fts-badge) for database rows in Plan 04"
  - "Paper footer (.site-footer with .footer-grid / .footer-col / .footer-bottom) replacing old bare footer markup"
  - "Section framing primitives (.section, .section.alt, .section-num, .section-head, .kicker)"
  - "Shared layout wrapper rules (max-width 1200px .container inside each chrome block)"
affects:
  - 01-03-home-editorial
  - 01-04-database-editorial-rows
  - 01-05-table-feed-partials
  - 01-06-visual-qa-sweep

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared chrome rendered through {% block nav %} / {% block footer %} — _header.html is itself the block content (no <header> wrapper), _footer.html likewise"
    - "Hardcoded Home crumb inside _header.html (callers pass crumbs from the database level onward)"
    - "Logo uppercasing via CSS text-transform + --tracking-caps (WARN-07) — NO Jinja |upper filter"
    - "New chrome CSS inserted BEFORE the tail `footer a:link` override so the override keeps winning the cascade against /-/static/app.css (WARN-05)"
    - "All chrome uses var(--*) tokens defined in Plan 01 — zero hardcoded hex in new rules"

key-files:
  created: []
  modified:
    - "templates/_header.html"
    - "templates/_footer.html"
    - "templates/database.html"
    - "templates/table.html"
    - "static/css/zeeker-base.css"

key-decisions:
  - "Hardcoded 'Home' as first crumb inside _header.html so every caller's crumb array starts from the db level — simpler API and eliminates the duplicated {'href':'/', 'label':'Home'} row in database.html/table.html"
  - "Insert new SHELL CHROME section immediately before the tail `footer a:link` override block (which plan 01-01 relocated to end-of-file). This preserves the tail-override invariant: `tail -20 | grep -q 'footer a:link'` still passes"
  - "Keep dead legacy selectors (.header-search, .header-left, .header-breadcrumb, .header-content, .hero-section, .database-card, .tagline, .footer-text, .footer-content) intact in zeeker-base.css — plans 03/04/05 will rewrite markup, removal is a polish pass (plan 06 or later)"
  - ".db-nav .menu uses both `color: var(--color-bg)` + `opacity: 0.8` then `opacity: 1` on hover (instead of a second color token) to stay faithful to sketch 001-D's hover tint"
  - ".db-toolbar uses `position: sticky; top: 0; z-index: var(--z-sticky)` so it pins under the nav — plan 04 controls placement, plan 02 just defines the class"
  - ".site-footer .footer-col a uses `font-size: var(--text-sm)` only (no explicit color) — the tail `footer a:link` specificity override still owns link color"
  - "CTA `.btn-ghost` uses inline rgba(245,242,234,…) values for border/background-tint — these encode the paper bg as a semi-transparent overlay on ink, which a token can't express without a new --color-bg-alpha-40 style token"
  - ".cat-pill.speech/.announcement use inline rgba(…) color mixes of ochre/terracotta — copied verbatim from the sketch source (001-home-editorial-hero/index.html) to match the reference exactly"

patterns-established:
  - "Chrome CSS is appended in one banner-delimited section (`/* =========== SHELL CHROME — phase 01 ============ */`) so future phases can locate/diff it easily"
  - "Hero, statband, toolbar, CTA, cat-pill, fts-badge classes are all defined in ONE plan so later waves only touch per-page templates (no CSS churn across plans 03/04/05)"
  - "Breadcrumb contract: callers declare `{% set breadcrumbs = [...] %}` in the `{% block nav %}` *before* including _header.html; the include picks up the variable at render time"
  - "Block-rename `footer_text` → `footer-bottom` class (template still uses `{% block footer_text %}` as the Jinja block name to preserve per-database override points, but the rendered HTML carries the new class)"

requirements-completed:
  - SC-01-dark-nav
  - SC-01-breadcrumb-mono
  - SC-01-hero-asymmetric
  - SC-01-petrol-statband
  - SC-01-sticky-toolbar
  - SC-01-footer-contrast

# Metrics
duration: ~12min
completed: 2026-04-19
---

# Phase 1 Plan 02: Shared Chrome Summary

**Cross-page editorial shell shipped — dark ink nav with ochre logo, mono breadcrumb strip, asymmetric-hero + petrol-statband + sticky-toolbar + dark-CTA + 4-col paper-footer component classes — all rendered through `_header.html` / `_footer.html` and all styled by a new `SHELL CHROME` CSS section in `zeeker-base.css` (inserted before the tail footer-link override so the cascade stays intact).**

## Performance

- **Duration:** ~12 min
- **Tasks:** 4 (1, 1.5, 2, 3)
- **Files modified:** 5

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite templates/_header.html as dark nav + breadcrumb strip** — `58e38f8` (feat)
2. **Task 1.5: Drop Home from caller breadcrumbs (now in _header.html)** — `d317f94` (fix)
3. **Task 2: Rewrite templates/_footer.html with site-footer class + footer-bottom** — `7a5ea0a` (feat)
4. **Task 3: Append SHELL CHROME CSS section (404 lines)** — `b281964` (feat)

_Plan metadata commit will be made by the orchestrator when it updates STATE.md / ROADMAP.md._

## Files Created/Modified

- `templates/_header.html` — replaced blurred-white header + search + nav `<ul>` with dark `<nav class="db-nav">` (logo + `.menu`) and optional `<div class="db-crumb">` (Home + iterated crumbs). The old `.header-search` form, `.header-breadcrumb` wrapper and `<header>` tag are gone. Jinja `{% block nav_items %}` is preserved for per-database override of menu contents.
- `templates/_footer.html` — wrapped in `<footer class="site-footer">`, renamed rendered `.footer-text` → `.footer-bottom`, changed fallback `site_title` from `Data Explorer` → `data.zeeker.sg`. `{% block footer_links %}` and `{% block footer_text %}` blocks preserved.
- `templates/database.html` — removed `{'href': '/', 'label': 'Home'}` from the `breadcrumbs` array (Home now rendered by `_header.html`).
- `templates/table.html` — same — removed the Home prefix from the `breadcrumbs` array.
- `static/css/zeeker-base.css` — appended 404 lines in a new banner-delimited `SHELL CHROME — phase 01` section, inserted BEFORE the existing tail `footer a:link` override (which remains in the last 20 lines).

## New Component Classes Shipped

| Class | Purpose | Consumer plan |
| --- | --- | --- |
| `.db-nav` | Dark ink nav bar (ink bg, ochre logo, white menu @80% opacity) | All pages (via _header.html) |
| `.db-nav .logo` | Ochre uppercase-via-CSS brand link (WARN-07) | All pages |
| `.db-nav .menu` | Right-aligned 4-link menu | All pages |
| `.db-crumb` | Mono/uppercase breadcrumb strip on warm bg-alt | database, table pages |
| `.db-crumb .sep` / `.current` | Separator glyph + petrol current-page marker | database, table pages |
| `.kicker`, `.section-label` | Mono terracotta section tag (with `— ` prefix) | 03, 04, 05 |
| `.section`, `.section.alt` | Numbered vertical-rhythm section container | 03, 04 |
| `.section-num` | Mono terracotta "№ 01" numbering | 03, 04 |
| `.section-head` + `.aside` | 1fr/320px head grid with h2/em italic accent | 03, 04 |
| `.db-header` + `.db-header-grid` | Asymmetric hero wrapper (1fr/320px, stacks <960px) | 03, 04, 05 |
| `.db-header h1 em` | Petrol italic accent inside hero h1 | 03, 04 |
| `.db-header .lede` | Muted subhead paragraph | 03, 04 |
| `.db-header .meta-col` | Right-rail dt/dd meta column with petrol top-border | 04 |
| `.db-statband` | Petrol full-bleed 4-col stat band | 03, 04 |
| `.db-statband .stat-num` / `.stat-label` | Ochre display-face number + mono uppercase label | 03, 04 |
| `.db-toolbar` | Sticky sub-toolbar under nav | 04 |
| `.db-toolbar-search` | Inline search pill (sunken-bg, border, radius-sm) | 04 |
| `.view-toggle` + `.view-toggle button.active` | Mono segmented control | 04 (if used) |
| `.cta` | Full-bleed dark CTA block | 03 |
| `.cta h2 em` | Ochre italic inside CTA headline | 03 |
| `.btn-primary` | Ochre-bg on ink button | 03 |
| `.btn-ghost` | Transparent-on-ink ghost button | 03 |
| `.cat-pill` + 4 variants (press-release, speech, announcement, newsletter) | Mono uppercase feed-card category pill | 05 |
| `.fts-badge` | Mono outlined FTS indicator | 04 |
| `.site-footer` | Paper-bg 4-col footer | All pages (via _footer.html) |
| `.site-footer .footer-grid` / `.footer-col` / `.footer-bottom` | Footer grid + column heading + bottom copyright strip | All pages |

## Caller Updates (Task 1.5)

The new `_header.html` hardcodes the first `Home` crumb, so the two caller templates had to drop that prefix:

- **`templates/database.html` `{% block nav %}`:** removed `{'href': '/', 'label': 'Home'}` — crumbs now start with `{'label': metadata.title | database|title}`.
- **`templates/table.html` `{% block nav %}`:** removed `{'href': '/', 'label': 'Home'}` — crumbs now start with `{'href': '/' ~ database, 'label': database|title}`.

No other blocks in `database.html` / `table.html` were touched (Plan 04 owns the `database_header` rewrite; `table.html` is otherwise out of scope this phase).

## Dead / Legacy Selectors Retained in zeeker-base.css

These selectors are no longer rendered by the rewritten `_header.html` / `_footer.html`, but are retained intact per the plan's critical-preservation note — other pages (developers, status, sources, about, how-to-use) may still reference them and removing them is a later polish pass:

| Selector | Occurrences | Notes |
| --- | --- | --- |
| `.header-content` | 2 | Old header grid wrapper |
| `.header-left` | 6 | Old logo/tagline anchor block |
| `.header-search` | 9 | Old sticky-white search form |
| `.header-search-icon` | 1 | Old search SVG |
| `.header-search-kbd` | 3 | Old keyboard shortcut hint |
| `.header-breadcrumb` | 6 | Old breadcrumb wrapper (replaced by `.db-crumb`) |
| `.tagline` | 2 | Old logo tagline line |
| `.footer-content` | 1 | Old footer container |
| `.footer-text` | 1 | Old footer bottom strip (rendered class now `.footer-bottom`) |
| `.hero-section` | 3 | Old home hero (Plan 03 will replace with `.db-header`) |
| `.database-card` | 6 | Old home database cards (Plan 04/05 will replace with editorial rows) |

None of these blocks cause any visual issue today — they're just unused rules.

## `s()` String Keys Referenced in New Templates

Only one string-manager helper call in the new templates:

- `s('site_title', 'data.zeeker.sg')` — used in `_footer.html` copyright strip (inside `{% block footer_text %}`).

The `_header.html` logo uses the plain `str_site_title|default('data.zeeker.sg', true)` variable (injected by string_manager), not the `s()` helper — matches the plan spec.

## Verification Results

All automated acceptance criteria pass:

**Task 1 (`_header.html`):**
- `<nav class="db-nav">` present ✓
- `<div class="db-crumb">` present ✓
- `class="logo"` present ✓
- `class="current"` present ✓
- `metadata.menu_links` referenced ✓
- `{% if link.href != '/' %}` filter retained ✓
- `header-search` absent ✓
- `|upper` absent (CSS-driven uppercase) ✓
- Logo fallback is lowercase literal `data.zeeker.sg` ✓
- No `<header>` wrapper ✓

**Task 1.5 (callers):**
- `grep "'label': 'Home'" templates/database.html` → no match ✓
- `grep "'label': 'Home'" templates/table.html` → no match ✓
- `grep "set breadcrumbs" templates/database.html` → 1 match ✓
- `grep "set breadcrumbs" templates/table.html` → 1 match ✓

**Task 2 (`_footer.html`):**
- `<footer class="site-footer">` present ✓
- `class="footer-grid"` present ✓
- `class="footer-col"` × 4 ✓
- `class="footer-bottom"` present ✓
- `{% block footer_links %}` + `{% block footer_text %}` retained ✓

**Task 3 (`zeeker-base.css`):**
- `/* =========== SHELL CHROME — phase 01 ============ */` banner present ✓
- All required selectors present: `.db-nav`, `.db-crumb`, `.db-header`, `.db-header h1 em`, `.db-statband`, `.db-toolbar`, `.kicker`, `.section-num`, `.cta`, `.cta h2 em`, `.btn-primary`, `.btn-ghost`, `.cat-pill.press-release/.speech/.announcement/.newsletter`, `.fts-badge`, `.site-footer`, `.site-footer .footer-grid`, `.site-footer .footer-col`, `.site-footer .footer-bottom` ✓
- `.db-nav .logo` block contains BOTH `text-transform: uppercase` AND `letter-spacing: var(--tracking-caps)` ✓
- Token counts: `--color-ochre` = 11 (≥5), `--color-terracotta` = 6 (≥4), `var(--color-accent)` = 63 (≥10) ✓
- `footer a:link` block still present and still in last 20 lines of file ✓
- Line count: 3,176 → 3,580 (+404, within 350–450 target) ✓
- Braces balanced: 495 open / 495 close ✓

**Overall success criteria:**
- All 4 tasks committed atomically with individual commits ✓
- No modifications to STATE.md / ROADMAP.md ✓
- No files modified outside the plan's `files_modified` list (plus database.html/table.html which Task 1.5 explicitly authorizes) ✓

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All classes defined are consumed by later waves (Plan 03 uses .db-header, .cta, .btn-primary, .btn-ghost, .db-statband; Plan 04 uses .db-toolbar, .db-header .meta-col, .fts-badge; Plan 05 uses .cat-pill variants). The `.view-toggle` class has no current consumer but is part of the sketch's sticky-toolbar vocabulary and documented for future pivots.

## Follow-up Cleanup Noticed (Not Done — Out of Scope)

- **Dead selectors from old header/footer markup** (see table above) — removal deferred to a polish pass (likely plan 01-06 visual-qa-sweep or a later standalone cleanup).
- **`templates/_header.html` no longer emits `/-/search` link** — the old header had the page-level search form. If analytics show users relied on the header `/` hotkey search, plan 01-06 (visual QA) may want to add a single-character search shortcut back.
- **Logo font-weight 700 in `.db-nav .logo` but Fraunces `@font-face` only loads 400/500.** At 700 the browser will synthesize bold. If this looks crusty on QA, plan 01-06 can either (a) drop the synthesized weight to 500, or (b) bake a Fraunces-700 woff2 into `static/fonts/`.
- **`.view-toggle` defined but unused** — kept because sketch 002/003 reference it for table-page view switchers, but no plan in this phase renders it. Safe to leave; can be removed in cleanup if still unused after phase 02.
- **CSS still references back-compat spacing aliases** in old component blocks (`--space-md`, `--space-lg`, etc.) — Plan 01-01 flagged these; not addressed here either.

## Self-Check: PASSED

- `.planning/phases/01-editorial-shell-home-inventory/01-02-shared-chrome-SUMMARY.md` — FOUND (this file)
- `templates/_header.html` — FOUND (modified)
- `templates/_footer.html` — FOUND (modified)
- `templates/database.html` — FOUND (modified, breadcrumbs only)
- `templates/table.html` — FOUND (modified, breadcrumbs only)
- `static/css/zeeker-base.css` — FOUND (modified, +404 lines)
- Commit `58e38f8` (Task 1) — FOUND in git log
- Commit `d317f94` (Task 1.5) — FOUND in git log
- Commit `7a5ea0a` (Task 2) — FOUND in git log
- Commit `b281964` (Task 3) — FOUND in git log

## Next Phase Readiness

- **Ready for Plan 01-03 (home-editorial):** `.db-header`, `.db-header-grid`, `.db-header h1 em`, `.db-header .lede`, `.db-statband`, `.cta`, `.btn-primary`, `.btn-ghost`, `.section`, `.section-head`, `.kicker` all defined. Home page rewrites `templates/index.html` main-content block only.
- **Ready for Plan 01-04 (database-editorial-rows):** `.db-header` + `.meta-col`, `.db-toolbar` + `.db-toolbar-search`, `.db-statband`, `.fts-badge` all defined. Database page rewrites `templates/database.html` main-content block only.
- **Ready for Plan 01-05 (table-feed-partials):** `.cat-pill.press-release`, `.cat-pill.speech`, `.cat-pill.announcement`, `.cat-pill.newsletter` all defined. Feed/card partials can reference them verbatim.
- **No blockers** for Wave 3 plans (03/04/05) to execute in parallel — all shared chrome CSS lives in one file now, so later plans only touch per-page templates.

---
*Phase: 01-editorial-shell-home-inventory*
*Completed: 2026-04-19*

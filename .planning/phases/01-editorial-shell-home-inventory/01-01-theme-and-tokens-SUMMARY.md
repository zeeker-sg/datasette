---
phase: 01-editorial-shell-home-inventory
plan: 01
subsystem: ui
tags:
  - css
  - design-tokens
  - theme
  - typography
  - fraunces
  - inter
  - jetbrains-mono
  - civic-broadsheet

# Dependency graph
requires: []
provides:
  - "Civic-broadsheet color tokens (warm paper #F5F2EA + deep petrol #0A4F55 + ochre #C08A2E + terracotta #B5552F + ink #14201F) exposed as CSS custom properties"
  - "Fraunces/Inter/JetBrains-Mono typography tokens (--font-display, --font-body, --font-mono) and full type scale (--text-2xs through --text-7xl + --text-display)"
  - "4px-based spacing scale (--space-1 through --space-32) alongside back-compat named spacing (--space-xs..--space-3xl)"
  - "Italic-accent-on-h1 signature: `h1 em` paints petrol italic, `h1 .und` paints 4px ochre underline"
  - "Global `a, a:link, a:visited { color: var(--color-accent) }` beating Datasette app.css #276890 without !important"
  - "Inert alternate-theme stubs: [data-theme=\"broadsheet\"] and [data-theme=\"petrol-ink\"] (defined but not wired)"
affects:
  - 01-02-shared-chrome
  - 01-03-home-editorial
  - 01-04-database-editorial-rows
  - 01-05-table-feed-partials
  - 01-06-visual-qa-sweep

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS custom properties in :root as the single source of truth — no component-level hardcoded hex"
    - "Matching-specificity a/footer-a overrides (no !important) to beat Datasette /-/static/app.css"
    - "Italic accent-on-h1 signature via h1 em / h1 .und selectors"
    - "Alternate theme stubs via [data-theme=\"...\"] attribute selectors"

key-files:
  created: []
  modified:
    - "static/css/zeeker-base.css"

key-decisions:
  - "--color-ink set to #14201F (near-black with petrol hint, per theme-system.md) instead of sketch theme's #1B1B1B — matches the --color-text value and plan spec"
  - "Back-compat named spacing tokens (--space-xs..--space-3xl) retained alongside new 4px numeric scale so existing components (2,900+ CSS lines) don't break before later plans migrate them"
  - "Back-compat color aliases (--color-bg-primary, --color-bg-secondary, etc.) retained for same reason"
  - "--color-accent-primary alias kept pointing at #0A4F55 so static/js/zeeker-base.js ZeekerEnhancer keeps working"
  - "Footer a:link override RELOCATED from mid-file (line ~2887) to absolute tail of file (now in last 20 lines) so the cascade still beats /-/static/app.css — plan's acceptance criterion `tail -20 | grep -q 'footer a:link'` now passes"
  - "No !important used on a:link or body — matching specificity is sufficient"

patterns-established:
  - "Token-first CSS: all colors, typography, spacing, radii, shadows referenced via var(--*) — zero hardcoded hex in new/rewritten rules"
  - "Datasette app.css override via matching-specificity selectors at tail of extra_css (a:link and footer a:link) rather than !important"
  - "Italic-accent signature: `<h1>… <em>word</em> <span class=\"und\">word</span> …</h1>` pattern from theme-system.md is globally styled — templates in 01-02/01-03/01-04 can now use it verbatim"

requirements-completed:
  - SC-01-palette-applied
  - SC-01-typography-applied
  - SC-01-spacing-scale

# Metrics
duration: ~18min
completed: 2026-04-19
---

# Phase 1 Plan 01: Theme & Tokens Summary

**Civic-broadsheet design tokens (warm-paper + deep-petrol + ochre + terracotta palette, Fraunces/Inter/JetBrains-Mono typography, 4px spacing scale, italic-accent-on-h1 signature) baked into `static/css/zeeker-base.css` — foundation for all component CSS in plans 01-02 through 01-05.**

## Performance

- **Duration:** ~18 min
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Replaced the "white and plain" :root token layer with the full civic-broadsheet palette (warm paper `#F5F2EA`, deep petrol `#0A4F55`, ochre `#C08A2E`, terracotta `#B5552F`, ink `#14201F`), plus back-compat aliases so existing components keep working.
- Added the full editorial type scale up to `--text-7xl: 7.5rem`, the 4px spacing scale (`--space-1` through `--space-32`), leading/tracking tokens, and paper-like elevation shadows.
- Added the `h1 em` (petrol italic) and `h1 .und` (ochre 4px underline) signature pattern globally — templates in later plans can use `<em>` and `<span class="und">` inside headings with zero extra CSS.
- Added `a, a:link, a:visited { color: var(--color-accent) }` to beat Datasette's `/-/static/app.css` `a:link { color: #276890 }` via matching specificity (no `!important`).
- Relocated the `footer a:link` specificity override from mid-file to absolute tail so it stays in the last 20 lines of the file (plan's hard acceptance criterion) and keeps winning against app.css's `footer a:link`.
- Added inert `[data-theme="broadsheet"]` and `[data-theme="petrol-ink"]` stubs copied verbatim from the sketch source theme — defined-but-not-wired per scope-out.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace :root token block with civic-broadsheet palette + type scale + spacing scale** — `c990f90` (feat)
2. **Task 2: Rewrite body/headings/links base styles + italic-accent-on-h1 signature** — `33fccb1` (feat)

_Plan metadata commit will be made by the orchestrator when it updates STATE.md / ROADMAP.md._

## Files Created/Modified

- `static/css/zeeker-base.css` — (1) replaced `:root` token block with civic-broadsheet palette + Fraunces/Inter/Mono typography + 4px spacing scale; (2) appended two alternate-theme stubs; (3) rewrote `html` / `body` / `h1-h6` / `a` / `code` / `pre` / `kbd` base styles; (4) added `h1 em` / `h1 .und` / `h2 em` etc. italic-accent signature selectors; (5) added matching-specificity `a, a:link, a:visited` override; (6) relocated `footer a:link` override block from line ~2887 to end-of-file (now in last 20 lines).

## Preserved Verbatim

These existing rules were explicitly preserved and verified post-edit:

- **`@font-face` declarations** for Inter / JetBrains Mono / Fraunces (all 3 still present, pointing at `/static/fonts/*-latin.woff2`)
- **`:focus-visible` keyboard focus ring rules** (6 selectors still present)
- **`@media (prefers-reduced-motion)` blocks** (2 blocks still present)
- **Prism SQL syntax highlighting** (`.token.keyword`, `.token.string`, `.token.number`, `.token.function`, `.token.comment`, `.token.operator`, `.token.variable` all still present and still referencing `--color-accent`)
- **`a.btn` / `a.cta-primary` / `a.cta-secondary` / `.header-left` no-underline override** (retained in position, immediately after the new `a:hover` rule — ordering matters because `a:hover` now underlines by default)
- **`footer a:link` / `footer a:visited` / `footer a:active` specificity override** (relocated to absolute tail of file, still beats Datasette's `app.css` footer rule, still in last 20 lines)
- **`.header-search`, `.sr-only`, mobile `@media (max-width: 768px)` block** — all untouched

## Back-compat Aliases Retained

These aliases were retained so existing CSS (2,900+ pre-existing lines) doesn't regress before plans 01-02..01-05 migrate component styles:

**Colors:**
- `--color-bg-primary` → `#F5F2EA` (same as `--color-bg`)
- `--color-bg-secondary` → `#FFFFFF` (same as `--color-surface`)
- `--color-bg-tertiary` → `#EEE9DC` (same as `--color-bg-alt`)
- `--color-bg-elevated` → `#F0ECE0` (same as `--color-surface-sunken`)
- `--color-surface-raised` → `#FFFFFF`
- `--color-text-primary` → `#14201F` (same as `--color-text`, `--color-ink`)
- `--color-accent-primary` → `#0A4F55` (same as `--color-accent`; **JS dependency** — `static/js/zeeker-base.js` references this name)

**Spacing (named):**
- `--space-xs: 8px` (maps to new `--space-2`)
- `--space-sm: 12px` (maps to `--space-3`)
- `--space-md: 16px` (maps to `--space-4`)
- `--space-lg: 24px` (maps to `--space-6`)
- `--space-xl: 32px` (maps to `--space-8`)
- `--space-2xl: 48px` (maps to `--space-12`)
- `--space-3xl: 64px` (maps to `--space-16`)

**Radius:**
- `--radius-xl: 16px` and `--radius-2xl: 16px` retained (sketch theme defines only `--radius-xs/sm/md/lg/full`, but existing components reference `--radius-xl`)

## Decisions Made

- **Ink color: #14201F (per theme-system.md + plan), not #1B1B1B (per sketch default.css).** The skill's theme-system.md reference explicitly defines `--color-ink: #14201F` ("near-black with a petrol hint") and this is what the plan's token block specifies. The sketch's default.css used `#1B1B1B` but that's the source-of-theme reference, not the contract. Going with theme-system.md + plan spec.
- **Keep back-compat named spacing (`--space-xs`, `--space-md`, etc.) as fixed px values rather than aliases to numeric scale.** Faster than chasing down every component that references them, and the pixel values are identical anyway (`--space-xs: 8px` === `--space-2: 8px`). Later plans can migrate when they rewrite components.
- **Relocate `footer a:link` override block to end-of-file rather than duplicate it.** The plan's acceptance criterion `tail -20 | grep -q 'footer a:link'` was a hard gate. The block was originally at line ~2887 with ~180 lines of mobile/accessibility CSS following it. Moving (not duplicating) is cleaner and still wins the cascade since it's still later in the extra_css than Datasette's `/-/static/app.css`.

## Deviations from Plan

None — plan executed exactly as written.

The one judgment call (relocating the footer override to end-of-file rather than leaving it mid-file) is explicitly required by the plan's Task 1 acceptance criterion `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` and documented in the plan's `<critical_preservation>` note ("Must remain at the end of the file (where it wins the cascade against Datasette's app.css)"). Not a deviation — a contractual requirement.

## Issues Encountered

None.

## Follow-up Cleanup Noticed (Not Done — Out of Scope)

Scanning the rest of `static/css/zeeker-base.css` (lines 334-2950) revealed these pre-existing references that later plans should migrate or clean up:

- **Hardcoded hex in component sections:** A grep for `#[0-9A-Fa-f]{6}` in lines 334+ shows pre-existing component rules still using hardcoded hex instead of tokens (e.g. card hover shadows, category pill colors). Plans 01-03/01-04/01-05 append new component sections and could migrate the old ones in passing.
- **`--color-bg-primary` usage in pre-existing rules:** Many component rules reference `--color-bg-primary` (old alias). The alias points at the correct new value (`#F5F2EA`), so no visual regression, but later plans could migrate these to `--color-bg` directly to reduce indirection.
- **`--text-4xl: 3rem` changed from `2.25rem` → `3rem`:** Existing components that assumed `--text-4xl == 2.25rem` for mid-hero display sizes will now render larger. This is intentional (broadsheet scale) but may require small tweaks in plan 01-03 hero sizing.
- **`line-height: 1.3` in pre-existing h1-h6 was replaced by `var(--leading-tight)` (1.05).** Tighter headline leading is the editorial move, but existing long multi-line headings may render differently. Visual QA sweep (plan 01-06) will catch regressions.
- **`h1 { font-size: --text-5xl (4rem) }` is a big jump from prior `--text-4xl (2.25rem → 3rem)`.** Intentional, but cards/rows that embed an h1 (e.g. table-of-contents list items) may overflow. Plans 01-03/01-04 will need to downscale embedded h1s to `h2` semantics or override with `font-size:` at card scope.

None of these were fixed in this plan — they're component-layer concerns for later plans.

## Verification Results

All automated acceptance criteria from `<verify><automated>` blocks pass:

**Task 1:**
- `grep -c -- '--color-bg: #F5F2EA'` → 1 ✓
- `grep -c -- '--color-accent: #0A4F55'` → 1 ✓
- `grep -c -- '--color-ochre: #C08A2E'` → 1 ✓
- `grep -c -- '--color-terracotta: #B5552F'` → 1 ✓
- `grep -c -- '--color-ink: #14201F'` → 1 ✓
- `grep -c -- "--font-display: 'Fraunces'"` → 1 ✓
- `grep -c -- '--text-7xl: 7.5rem'` → 1 ✓
- `grep -c -- '--space-16: 64px'` → 1 ✓
- `grep -q 'data-theme="petrol-ink"'` → present ✓
- `grep -q '--color-accent-primary'` → present ✓
- `tail -20 static/css/zeeker-base.css | grep -q 'footer a:link'` → present ✓

**Task 2:**
- `grep -q 'background: var(--color-bg)'` → present ✓
- `grep -q 'h1 em'` → present ✓
- `grep -q 'color: var(--color-accent)'` → present ✓
- `grep -q 'text-decoration-color: var(--color-ochre)'` → present ✓
- `grep -q 'a, a:link, a:visited'` → present ✓
- `grep -q 'footer a:link'` → present ✓
- `grep -q 'a.btn'` → present ✓
- `tail -20 … | grep -q 'footer a:link'` → present ✓

**Plan-level verification:**
- `grep -c -- '--color-'` returns 359 (≥30 required) ✓
- `grep -c 'Fraunces'` returns 3 (≥2 required) ✓
- File line count: 3,075 → 3,176 (+101, well within ±500 constraint) ✓
- CSS braces balanced: 420 open / 420 close ✓
- `@font-face` declarations: 3 (Inter, JetBrains Mono, Fraunces) ✓
- Prism `.token.keyword` still present ✓
- `:focus-visible` rules: 6 selectors still present ✓
- `prefers-reduced-motion` blocks: 2 still present ✓
- No new `!important` on `a:link` or body ✓
- `templates/database.html` NOT modified ✓

Manual browser verifications (items 3-6 in plan's `<verification>` block) require the dev server running — not executed automatically. These are best run by the orchestrator or plan 01-06 visual-qa-sweep.

## Self-Check: PASSED

- `.planning/phases/01-editorial-shell-home-inventory/01-01-theme-and-tokens-SUMMARY.md` — FOUND
- `static/css/zeeker-base.css` — FOUND (modified)
- Commit `c990f90` — FOUND in git log
- Commit `33fccb1` — FOUND in git log

## Next Phase Readiness

- **Ready:** All token primitives are in place. Plan 01-02 (shared chrome) can reference `--color-accent`, `--color-ochre`, `--color-terracotta`, `--color-ink`, `--font-display`, `--font-mono`, `--space-*`, `--tracking-caps`, etc. directly.
- **Ready:** The `h1 em` / `h1 .und` signature is globally wired — 01-03 (home) hero can use `<h1>Public data, <em>rendered</em> <span class="und">legible</span>.</h1>` verbatim and it will just work.
- **Ready:** `--color-accent-primary` alias preserved, so `static/js/zeeker-base.js` ZeekerEnhancer has no regressions.
- **Ready:** Alternate-theme stubs are defined but not wired — if plans 01-02..01-06 reveal a need for dark mode or the broadsheet alternate, flipping `<html data-theme="petrol-ink">` is all that's needed.
- **No blockers** for plan 01-02.

---
*Phase: 01-editorial-shell-home-inventory*
*Completed: 2026-04-19*

# Sketch Wrap-Up Summary

**Date:** 2026-04-19
**Sketches processed:** 4 (all included)
**Design areas:** Theme system · Shell & chrome · Home layout · Directory & feed lists · Row reading layouts
**Skill output:** `./.claude/skills/sketch-findings-zeeker-datasette/`

## Included Sketches

| # | Name | Winner | Design Area |
|---|------|--------|-------------|
| 001 | home-editorial-hero | D — synthesis: editorial shell + rotating-accent card grid | Home layout (+ theme, chrome) |
| 002 | database-table-grid | B — editorial list (no taxonomy) | Directory & feed lists |
| 003 | row-as-article | pending — 3 generic variants (magazine / broadsheet / structured) | Row reading layouts |
| 004 | table-as-news-archive | A — news feed with faceted sidebar, content-agnostic | Directory & feed lists |

## Excluded Sketches

_None._

## Design Direction

Civic broadsheet editorial for a long-text data archive. The V2 shell already defined deep petrol and Fraunces serif as ingredients but wasn't spending them; sketches explore color-confident editorial typography that signals "civic data platform" with craft, not a default template.

**Palette:** warm paper `#F5F2EA` + deep petrol `#0A4F55` + ochre `#C08A2E` + terracotta `#B5552F` + ink `#14201F`.
**Typography:** Fraunces 400/500 (italic accent on H1 `<em>`) up to 5–7rem; Inter 300–500 body; JetBrains Mono for data/metadata.
**Chrome:** dark ink nav, breadcrumb strip on warm paper-alt, asymmetric hero (7fr/5fr), petrol stat band, sticky toolbar, light footer.
**Inventory pages:** editorial full-width rows with display-serif titles + mono metadata. No grouping, no content-type specialization.
**Row pages:** content-agnostic article layout with field-mapping per table schema. Body in Fraunces opsz-tuned at 60–68ch measure.

## Key Decisions

1. **Spend the palette.** Accent colors (petrol, ochre, terracotta) rotate through card borders and category pills, not background fills. The petrol stat band is the one full-bleed colored moment per page.
2. **Italic-accent H1 is the signature.** Every major heading has one italicized word in `--color-accent`, often paired with an underlined span in ochre decoration color.
3. **Editorial rows beat card grids for inventories at 20+ items.** Uniform vertical rhythm, right-aligned counts, no grid reflow anxiety.
4. **No content-type-specific layouts.** News, judgment, and guide rows all fit one generic article template with field mapping per table.
5. **Use `_table-{db}-{table}.html` partial, not full `table.html` replacement.** Keeps Datasette's filter/facet/FTS/pagination/export machinery working.
6. **Light footer needs specificity-matched `a:link` override.** Datasette's `app.css` ships near-white footer link colors that are invisible against our paper footer.

## Open Questions (for next phase)

- Sketch 003 row layout — no single winner yet; pick one (or define content-type-conditional slots) when `row.html` customization gets built.
- "Data Guide" footer block (About / Licence / Source / Suggested Uses) not sketched — may want its own treatment.
- Home page copy "n agencies across m domains" treatment vs. current "12 databases" — cross-database story unresolved.
- Mobile at < 600px — all sketches collapse cleanly but no dedicated mobile-only pass.
- Dark `petrol-ink` theme is defined but untested at scale.

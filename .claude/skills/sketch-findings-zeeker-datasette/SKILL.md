---
name: sketch-findings-zeeker-datasette
description: Validated design decisions, CSS patterns, and visual direction from sketch experiments for zeeker-datasette. Auto-loaded during UI implementation. Covers civic-broadsheet editorial palette (warm paper + deep petrol + ochre + terracotta), Fraunces/Inter/JetBrains-Mono typography, shared shell chrome (dark nav + breadcrumb + hero + petrol stat band + sticky toolbar + footer), home card grid, editorial-list pattern for database/table pages, and row-reading layouts for long-text content (news, judgments, legal guides).
---

<context>
## Project: zeeker-datasette

Civic data platform built on Datasette. The V2 generic base shell already had the deep petrol palette (`#0A4F55`) and Fraunces serif defined, but they were barely being spent — the UI read as "white and plain, no design." Four sketch sessions explored how to make the UI feel like a civic broadsheet with color-confident editorial typography, validated against real data shapes (SG Government Newsrooms, Zeeker-Judgements, Sglawwatch legal guides).

Reference points: The Pudding, ProPublica Data Store, Our World in Data, UK Government Digital Service (but warmer), data.gov.sg (but with more craft).

Sketch sessions wrapped: 2026-04-19
</context>

<design_direction>
## Overall Direction

**Civic broadsheet editorial for a long-text data archive.**

- **Palette:** warm paper `#F5F2EA` + deep petrol `#0A4F55` + ochre `#C08A2E` + terracotta `#B5552F` + ink `#14201F`. Used with confidence — accent colors on borders, small fills, text; almost never as large background fills except the petrol stat band.
- **Typography:** Fraunces 400/500 (italic accent on H1 `<em>`) for all display slots up to 5–7rem; Inter 300–500 for body; JetBrains Mono for kickers, dates, SHA ids, facet labels.
- **Layout:** asymmetric grids (7fr/5fr hero, 1fr/sidebar content), numbered section framing (`№ 01 · Databases`), full-bleed petrol stat bands, editorial rows over card grids for inventories at scale.
- **Interaction:** subtle transitions (0.15s ease), left-edge slider bar on row hover, translateY(-2px) + soft shadow lift on cards, drop cap on first paragraph of article-style rows.
- **Datasette integration:** override `index.html`, `database.html`, `row.html` as full templates; use `_table-{db}-{table}.html` partial for feed-style table rendering without losing Datasette's filter/facet/FTS/pagination/export machinery.
</design_direction>

<findings_index>
## Design Areas

| Area | Reference | Key Decision |
|------|-----------|--------------|
| Theme system | `references/theme-system.md` | Palette, Fraunces/Inter/Mono typography, 4px spacing scale, italic-accent-on-H1 signature |
| Shell & chrome | `references/shell-and-chrome.md` | Dark ink nav, breadcrumb strip, asymmetric hero, petrol stat band, sticky toolbar — shared across every page |
| Home layout | `references/home-layout.md` | Editorial shell + card grid with rotating petrol/ochre/terracotta accent borders (synthesis of sketch 001 variants B + A) |
| Directory & feed lists | `references/directory-and-feed-lists.md` | Full-width editorial rows with display-serif titles — used for database-of-tables (002) and table-of-rows-as-news-archive (004). No grouping, no taxonomy. Category pills for row content types. |
| Row reading layouts | `references/row-reading-layouts.md` | Three variant layouts (magazine / broadsheet / structured hybrid), all content-agnostic via field-mapping table. Body in serif Fraunces at 60–68ch. No per-content-type templates. |

## Theme

The winning theme file is at `sources/themes/default.css` — CSS custom properties only, no component styles. Three alternate themes documented for future switching: `[data-theme="broadsheet"]` (cream + ink-red) and `[data-theme="petrol-ink"]` (dark mode).

## Source Files

Original sketch HTML files are preserved under `sources/`:
- `001-home-editorial-hero/index.html` — four variants; winner D (synthesis tab)
- `002-database-table-grid/index.html` — four variants; winner B (editorial list tab)
- `003-row-as-article/index.html` — three variants; no single winner, all three valid for different content types
- `004-table-as-news-archive/index.html` — three variants; winner A (news feed tab)

Every sketch has a companion `README.md` with the design question, variant descriptions, and "what to look for" evaluation criteria. The sketch toolbar (bottom-right of each HTML) flips between the three candidate themes.

## Datasette-specific implementation notes

See also `.planning/notes/datasette-styling-limits.md` for the 4-layer constraint map (templates, app.css, built-in table HTML, fixed URLs). Key points:

- Datasette's `app.css` wins specificity wars against bare selectors. Use matching-specificity overrides for `a:link`, `footer a`, etc.
- `_table-{db}-{table}.html` partial replaces only the row-list block, keeping filters/facets/FTS/pagination/export intact. This is the right seam for news-feed rendering.
- `render_cell` plugin hook is for cell value formatting, not row layout restructuring.
- `row.display("col")` inside templates preserves foreign-key and `datasette-render-markdown` behavior.
- `metadata.get('tables', {}).get(name)` is the safe access pattern; raw `metadata.tables[name]` raises under StrictUndefined when the tables key is absent.
</findings_index>

<metadata>
## Processed Sketches

- 001-home-editorial-hero
- 002-database-table-grid
- 003-row-as-article
- 004-table-as-news-archive
</metadata>

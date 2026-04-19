---
sketch: 002
name: database-table-grid
question: "How should 20+ tables read on a database page without becoming a wall of cards?"
winner: "B"
tags: [database, list, cards, inventory]
---

# Sketch 002: Database table grid

## Design Question
The current `/fixtures` page renders 24+ table cards as a wall of text with default link styling, no accent colors, and collapsed key-column sections. How should this scale — dense cards, editorial list, or grouped categories?

All three variants reuse the winning shell from sketch 001 (dark nav, warm hero with italic Fraunces, petrol stat band, toolbar).

## How to View
```
open .planning/sketches/002-database-table-grid/index.html
```

## Variants

- **A · Dense accent cards** — 3-column grid of 24 cards with rotating accent border (petrol/ochre/terracotta), mono index numbers, column lists, per-card action chips (Explore / CSV / JSON). Feels like a library card catalogue.
- **B · Editorial list (★ winner)** — Full-width rows with display-serif table names, inline column summary, right-aligned row counts, FTS badges. Reads like a broadsheet directory. Scales to 100+ tables with less visual furniture per item. Chosen because it needs no taxonomy to maintain.
- **C · Grouped categorized** — Tables grouped into semantic families (Core, Reference, Key Patterns, Edge Cases), each group with its own accent color, description, and compact item list. Most "designed" but requires maintaining a taxonomy.
- **D · Synthesis: grouped editorial list** — C's groups with B's rows. Explored but not chosen; the grouping cost isn't worth it for this surface.

## Decision Rationale
The editorial list (B) won over the grouped synthesis (D) because grouping requires a `group` field per table that would need to be configured per database. B works identically across every database with no taxonomy metadata — a better fit for a generic base shell.

## What to Look For
- **Density at scale** — which variant still reads well at 24 items? What about 100?
- **Where the eye lands first** — the name? The row count? The accent color?
- **Visual hierarchy** — is the card's action strip (A) helpful or cluttery? Does B's big row count pull attention from the name?
- **Maintenance cost** — C needs a `group` field per table. Worth it for the clarity gain?
- **Scan pattern** — horizontal (rows, in B) vs. grid (A) vs. nested (C): which matches how users actually shop for a dataset?

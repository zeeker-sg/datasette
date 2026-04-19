---
sketch: 003
name: row-as-article
question: "How does a row render when the content is a full press release / news article, not tabular data?"
winner: null
status: parked-future-feature
tags: [row, article, reading, long-text, future]
---

> **Parked.** Datasette's default row-detail page is not currently customized in zeeker. Keeping this sketch as a reference for future work if/when a custom `row.html` template gets built. Next (sketch 004) pivots to the table page, which is what was actually broken.


# Sketch 003: Row as article

## Design Question
Zeeker's SG Government Newsrooms database contains press releases, speeches, and announcements — long-form prose, not tabular data. Datasette's default row view renders a `<dl>` of `field: value`, which dumps the article body alongside the SHA-256 id as if they're equivalent. How should a row feel when the content IS the article?

## How to View
```
open .planning/sketches/003-row-as-article/index.html
```

## Variants

All three use the same sample ACRA press release so you can compare typography, metadata placement, and reading flow directly.

- **A · Magazine feature** — Bloomberg-Businessweek long-read. Kicker + display serif title, italic lede, drop cap on first paragraph, sticky metadata sidebar with record + export actions, "More from ACRA" strip at bottom. Reading-first; record is supporting actor.
- **B · Editorial broadsheet** — Most "designed." Dark full-bleed dateline strip (agency · date · category · record №), ultra-display headline with italic accent, 4-column meta strip, single centred reading column with pull quotes and section headings, source coda with double-rule divider. Almost no chrome; feels like a newspaper clipping.
- **C · Structured record hybrid** — Dual column: article left (compact reading measure, sans-serif body), full `dl` of raw fields right (id SHA-256, source_url, category, title, published_date, fetched_at, word_count, language). Keeps Datasette's developer/debugger utility while promoting the content field to hero.

## What to Look For
- **Reading comfort** — A and B use serif body (Fraunces opsz); C uses sans-serif (Inter). Which feels right for 5-minute reads?
- **Where the raw record goes** — sidebar (A), coda at bottom (B), or full right column (C)?
- **How the SHA id reads** — hidden in a "Record" block (A), stamped in dateline (B), displayed in full dl (C). The SHA is useful but not beautiful; how much deference does it get?
- **Source URL treatment** — a small "Source ↗" link in byline (A), centred coda with fetch fingerprint (B), first-class field in sidebar (C). Which signals provenance most strongly?
- **Related items** — present in A ("More from ACRA" strip), absent in B and C. Should every row offer lateral navigation?
- **Scale concern** — B is magnificent for one article but may feel same-y across 761 records. A and C have more chrome variation.

---
sketch: 004
name: table-as-news-archive
question: "How does the table page display rows when the content is press releases (long text), not tabular data?"
winner: "A"
tags: [table, archive, rows, long-text]
---

# Sketch 004: Table as news archive

## Design Question
The SG Government Newsrooms tables contain press releases, speeches, and announcements — long-text content. Datasette's default table view renders a wide HTML `<table>` where columns like `content` and `title` collide with narrow fields like `published_date` and `category`. For this data, the table page should feel like a **news archive**, not a spreadsheet.

## How to View
```
open .planning/sketches/004-table-as-news-archive/index.html
```

## Variants

All three render the same 20 realistic ACRA rows with categories (press-release / speech / announcement / newsletter) and real-shaped titles/excerpts.

- **A · News feed (★ winner)** — Reverse-chronological flat list. Each row: big Fraunces title, 2-line excerpt, mono byline with date + category pill + SHA id + source link. Sticky right sidebar with faceted counts (category, year). Closest to a press-page / blog index. Chosen because it scales uniformly to 361 items and preserves Datasette's faceted-browse UX without forcing a taxonomy.
- **B · Monthly archive** — Grouped by publication month with a sticky Fraunces month-header (large Fraunces roman + italic year + count badge). Inside each month, compact rows with a display-serif day number + title + excerpt + category pill. Feels like a newspaper archive.
- **C · Featured + list** — Top 2 most recent items get hero-card treatment (excerpt, petrol/ochre accent borders, prominent title). Below the double-rule, the remaining 18 render as a dense list: date · title · category pill. Implicit recency hierarchy; fastest scan-time.

## What to Look For
- **Scannability** — A (all equal) vs. B (grouped) vs. C (hierarchy). Which gets you to "oldest relevant entry" fastest?
- **Where the SHA/source hides** — inline in byline (A), absent from list view (B), in featured-card footer (C). Do you need the record identity at list level?
- **Facet placement** — sidebar (A), inline toolbar only (B, C). Faceted browsing is standard Datasette — where should those live here?
- **Density trade** — C lets 20 items fit on a tall screen; A shows 6-7 with full excerpts. Which fits the reading intent better?
- **Scaling to 361** — which pattern still works at page 10? B's monthly grouping gets heavy if there are 20+ months; A stays uniform; C's "featured" concept gets weird past page 1.
- **Category treatment** — color-coded pills on every variant; ochre = speech, petrol = press-release, terracotta = announcement, muted = newsletter. Readable?

## Implementation Hint

Do **not** replace the full `table.html`. Use Datasette's `_table-{database}-{table}.html` seam — it replaces *only* the `<table class="rows-and-columns">` block while keeping the filter form, FTS search, sort links, pagination, CSV/JSON export links, and the full advanced-export pane for free.

Per-table file per news table (e.g. `templates/_table-sg_govt_newsrooms-acra_news.html`), each doing `{% include "_partials/news_feed.html" %}` to share the card markup. Inside the partial, `display_rows` is iterable and `row.display("col")` gives the HTML-rendered value. Use `urls.row(database, table, row[primary_keys[0]])` for permalinks and `path_with_replaced_args(request, {'category': row['category']})` for clickable category pills.

See `.planning/notes/datasette-styling-limits.md` for full context variables available inside the partial.

## Content-agnostic usage

Applies to all long-text tables, not just news. The "feed card" pattern degrades gracefully:

| Table shape | Title | Primary pill | Date | Excerpt | Source |
|-------------|-------|--------------|------|---------|--------|
| `*_news` | `title` | `category` | `published_date` | first N chars of `content` | `source_url` |
| `judgments` | `case_name` | `court` + `citation` | `decision_date` | first tag of `subject_tags[]` as chips | `source_url` |
| `about_singapore_law` | `title` | `section` | `last_scraped` | (omit — `content_length` often 0) | `item_url` |

When there's no body to excerpt (guides with `content_length=0`), the card falls back to title + meta only — the layout stays uniform, just denser. No new template needed.

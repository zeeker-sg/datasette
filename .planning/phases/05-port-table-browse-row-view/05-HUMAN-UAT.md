---
status: partial
phase: 05-port-table-browse-row-view
source: [05-VERIFICATION.md]
started: 2026-04-25T16:30:00Z
updated: 2026-04-25T16:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual sweep — feed mode parity with sketch 004-A
expected: Visit /sglawwatch/headlines locally; confirm feed cards render with kicker (terracotta uppercase mono), italic-accent H1, hero with stat band, sticky toolbar with FTS + applied-chips + CSV/JSON exports, two-column layout (feed-main + sticky .facets sidebar with category facet block), pagination strip with Next → and 25/50/100 size selector
result: [pending]

### 2. Visual sweep — article mode parity with sketch 003-A
expected: Click into a headline; confirm row article layout shows kicker, italic-accent H1, byline+date, Fraunces opsz 11 body with drop cap on first paragraph, sticky aside with Record dl + Export links + back link, source coda double-rule
result: [pending]

### 3. Visual sweep — judgment mode parity with sketch 003-B
expected: Visit /Zeeker-Judgements/judgments/{pk} (after capturing real PK); confirm dark .dateline strip with ochre court agency + mono date, italic-accent H1, 4-column .judgment-meta grid, Fraunces body, .tag-chip row from subject_tags, .coda double-rule with source link + fingerprint
result: [pending]

### 4. End-to-end verifier against running stack
expected: docker compose up -d --build → bash scripts/verify_phase_05.sh exits 0 (with API-parity check #11 already retired). All 14 sections A-N green. Re-run after retirement commit 4c39405 to confirm Phase-5-specific sections (B-O) pass now that delegation chain no longer fails at Phase-2 #11.
result: [pending]

### 5. Longform-list mode parity with sketch 002-B variant without pills
expected: Visit /sglawwatch/about_singapore_law; confirm va-feed.longform-list renders without category pills (kicker styled muted), longer truncate(180) excerpts, and click-through goes to /sglawwatch/about_singapore_law/{pk} which renders longform mode (article reading column only, NO sidebar, NO drop cap)
result: [pending]

### 6. Tabular fallback row view with native <details> long-text expand
expected: Visit a row whose primary content is >200 chars; confirm native <details><summary>Show full content</summary> renders in tabular fallback row mode (D-04). Click summary; confirm full content appears and the .row-dd-preview hides via [open] CSS rule
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

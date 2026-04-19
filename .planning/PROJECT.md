# zeeker-datasette

## What it is
Civic data platform built on Datasette. Provides a branded, searchable web interface over SQLite databases containing Singapore government and legal content — press releases, speeches, court judgments, legal guides.

## V2 architecture
Generic TOML-driven base shell with light theme. Three-pass merge: base assets baked into Docker image, per-database overlays downloaded from S3 at startup. No hardcoded database references — templates work with any attached database.

## Current milestone: Editorial polish
Transform the "white and plain" V2 shell into a color-confident civic-broadsheet UI, driven by validated sketch findings.

## Reference artifacts
- `.claude/skills/sketch-findings-zeeker-datasette/` — packaged design decisions (theme, chrome, home, directory & feed lists, row reading)
- `.planning/sketches/` — source sketches and MANIFEST
- `.planning/notes/datasette-styling-limits.md` — Datasette template/CSS constraint map
- `CLAUDE.md` — project architecture and conventions

## Primary content types (data layer)
- News/speech/announcement/newsletter — `*_news` tables in agency databases
- Court judgments — `Zeeker-Judgements/judgments` (6,498 rows, 19 columns, subject_tags array)
- Legal guides — `Sglawwatch/about_singapore_law` (280 rows, 8 columns)

All three share a generic row anatomy (kicker / title / byline / body / tags / source / sidebar meta) — no content-type-specific templates.

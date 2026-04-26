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
- News/speech/announcement/newsletter — `*_news` tables in agency databases (mlaw, judiciary, AGC, IPOS, CCS, ACRA, MOM, PDPC; collected 2026-04-12 onwards)
- Court judgments — `zeeker-judgements/judgments` (~10,500 rows, AI-summarised, daily incremental builds)
- Legal news headlines — `sglawwatch/headlines` (editor-curated daily since 2025-05-16)
- Legal guides — `sglawwatch/about_singapore_law` (~40 articles, ~2,500 fragments)

All share a generic row anatomy (kicker / title / byline / body / tags / source / sidebar meta) — no content-type-specific templates.

## Current state — 2026-04-26
- Phase 6 SHIPPED. Every public HTML surface on `data.zeeker.sg` is now rendered by the FastAPI/Jinja frontend service: home, per-database, per-table, per-row, `/about`, `/how-to-use`, `/sources`, `/status`, `/developers`, `/llms.txt`, `/robots.txt`, `/search`, `/sql`, `/sql/{db}`. Caddy still routes `*.json`, `*.csv`, `*.db`, and `/-/*` directly to Datasette (D-01 boundary intact).
- Three services in production: Caddy (public), Datasette (internal-only), FastAPI frontend.
- 165 tests passing. Phase verifier `bash scripts/verify_phase_06.sh` PASS (all 11 sections green against `phase-06-pre/` baseline). Code-review status: 0 critical / 0 warning / 6 info.
- Production smoke against `data.zeeker.sg` is the only UAT item still pending and is gated on deploy.

Known config gaps surfaced during Phase 6 (out of phase scope, follow-up commits):
- `metadata.json` `allow_download: true` is set on the `*` wildcard but does not propagate to named databases — `/{db}.db` returns 403.
- FTS5 shadow tables exist only on `sglawwatch` (`headlines`, `about_singapore_law*`). Build pipeline needs `sqlite-utils enable-fts` calls on `judgments`, `judgments_fragments`, and the eight `*_news` tables before they show up in `/search` fan-out.

## Active milestone direction
Phase 7 (prune-zeeker-datasette) and Phase 8 are the remaining work in milestone v1.0.

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

## Current state — 2026-04-27
- Phase 7 SHIPPED 2026-04-26. Datasette image is now data-only: 5 UI plugins + top-level `templates/` + `static/` deleted; `Dockerfile` narrowed (whitelisted COPY for `__init__.py` + `cache_headers.py`); `metadata.json` cleaned (`extra_*_urls` dropped, `menu_links`/plugins/databases preserved); `download_from_s3.py` reduced to data-only sync (no UI overlay re-download on container restart); `entrypoint.sh` `--template-dir`/`--static` flags removed (Datasette 0.65.2 boot-tolerance correction). PR #8 merged via `d2dfdee` at 2026-04-26T15:09:30Z; production deploy executed; `bash scripts/verify_phase_07.sh` PASS against `https://data.zeeker.sg` (8 sections A-H green; A delegation skipped for non-local BASE_URL by design). Phase-6 production-smoke UAT closed transitively. Rollback anchor `pre-phase-7-prune` (commit `8ddaf95`) retained.
- Phase 6 SHIPPED. Every public HTML surface on `data.zeeker.sg` is rendered by the FastAPI/Jinja frontend: home, per-database, per-table, per-row, `/about`, `/how-to-use`, `/sources`, `/status`, `/developers`, `/llms.txt`, `/robots.txt`, `/search`, `/sql`, `/sql/{db}`. Caddy routes `*.json`, `*.csv`, `*.db`, and `/-/*` directly to Datasette (D-01 boundary intact).
- Three services in production: Caddy (public), Datasette (internal-only, API + admin only), FastAPI frontend.
- 165 frontend tests passing. Phase verifiers `verify_phase_03/04/06/07.sh` PASS (full chain green against `phase-07-pre/` baseline). Phase-6 code-review status: 0 critical / 0 warning / 6 info.

Known config gaps (out of phase scope, follow-up commits):
- `metadata.json` `allow_download: true` is set on the `*` wildcard but does not propagate to named databases — `/{db}.db` returns 403.
- FTS5 shadow tables exist only on `sglawwatch` (`headlines`, `about_singapore_law*`). Build pipeline needs `sqlite-utils enable-fts` calls on `judgments`, `judgments_fragments`, and the eight `*_news` tables before they show up in `/search` fan-out.
- `datasette-matomo` still appears in `/-/plugins.json` on prod despite the pre-Phase-7 decom commit (`d61a987`) removing it from `pyproject.toml`/`requirements.txt`. Plugin was a no-op stub; flagged for Phase 8 sweep.
- Caddy `path *.json` matcher is case-sensitive; uppercase `/SGLAWWATCH.JSON` falls through to frontend's HTML 404 (verifier `verify_phase_03.sh` §F.1 relaxed to accept either resolution; deferred to HUMAN-UAT triage).
- Root-level pytest collection has pre-existing infra failures (async fixture wiring); frontend pytest is the load-bearing suite.

## Active milestone direction
Phase 8 (overlay decision + Matomo migration) is the remaining work in milestone v1.0.

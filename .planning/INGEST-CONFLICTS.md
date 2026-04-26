## Conflict Detection Report

> Operation: ingest. Mode: merge. Docs ingested: 1 PRD (`prd-zeeker-frontend-split.md`).

### BLOCKERS (0)

_None._ No locked decisions exist in the current `.planning/` state (no `<decisions>` blocks in `PROJECT.md`, no per-phase `CONTEXT.md` files), so no LOCKED-vs-LOCKED contradiction is possible. The ingested PRD is itself `Status: Draft` (not locked).

### WARNINGS (1)

[WARNING] PRD strategic direction conflicts with active milestone M1's investment thesis
  Found: `prd-zeeker-frontend-split.md` §2 explicitly argues "Continuing to patch templates produces drift" and §3 sets the goal "Escape Datasette's template override surface — no more overriding `database.html`, `table.html`, or fighting `app.css` specificity." The migration plan (§10 Step 5) terminates with deletion of `templates/` and `static/` from the datasette package.
  Found: existing `.planning/ROADMAP.md` Milestone M1 "Editorial polish" is mid-flight — it invests in the Datasette template surface (`templates/_header.html`, `_footer.html`, `templates/index.html`, `templates/database.html`, `_table-{db}-{table}.html` partials, `static/css/zeeker-base.css` token system) precisely the surfaces the PRD proposes to delete.
  Impact: Naive merge would append M2 phases that delete the artifacts produced by M1 plans 01-01..01-06, wasting M1's ongoing work or making M1 obsolete on completion. Two viable framings exist and synthesis cannot pick:
    (a) PRD becomes a successor milestone M2, executed *after* M1 ships (M1 work is harvested — V2 templates inform the FastAPI Jinja templates that replace them);
    (b) PRD supersedes M1 entirely — pause/abort M1 plans, redirect effort to the architectural split.
  → User must choose framing (a) or (b) before routing. Framing affects: M1 status (continue vs pause), where ingested phases attach in ROADMAP.md, and whether existing M1 SUMMARY.md artifacts feed forward as references.

### INFO (3)

[INFO] No ADRs ingested
  Note: PRD's Appendix A "Decision log" lists 6 architectural choices (suffix routing, FastAPI+Jinja, Caddy, HTTP data access, etc.) but they're PRD-level proposals, not ratified ADRs (`Status: Accepted`). They are recorded in `.planning/intel/decisions.md` with `Locked: false`. Promote to ADR files (e.g., `docs/adr/0001-suffix-routing.md` with `Status: Accepted`) and re-ingest if you want them treated as locked downstream.

[INFO] PRD cross-references existing repo doc
  Note: PRD §1 cross-refs `.planning/notes/datasette-styling-limits.md` which already exists in the repo as constraint context. No conflict — synthesis preserves the reference in `.planning/intel/context.md`.

[INFO] Out-of-scope fences are aligned with current project assumptions
  Note: PRD Appendix B explicitly does NOT touch `zeeker.toml`, S3 bucket layout, refresh cron, or the data-scraping projects. These align with the implicit boundaries of the existing `.planning/PROJECT.md` ("V2 architecture: generic TOML-driven base shell with light theme … per-database overlays downloaded from S3"). No conflict.

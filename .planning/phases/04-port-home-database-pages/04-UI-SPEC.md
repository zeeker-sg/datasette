# Phase 4: Port home + database pages — UI Design Contract

**Purpose:** Satisfy the UI-phase gate. The authoritative design contract for this project lives in the `sketch-findings-zeeker-datasette` skill (auto-loaded during UI implementation). This document is a thin wrapper that identifies the Phase-4-specific harvest deltas and acceptance criteria — it does NOT redefine the design.

---

## Primary Design Contract

**Read first:** `.claude/skills/sketch-findings-zeeker-datasette/SKILL.md`

That skill is load-bearing. It covers:
- Palette (warm paper `#F5F2EA` + deep petrol `#0A4F55` + ochre `#C08A2E` + terracotta `#B5552F` + ink `#14201F`)
- Typography (Fraunces + Inter + JetBrains Mono; italic-accent H1 with colored `<em>`)
- Shell chrome (dark nav + breadcrumb + hero + petrol stat band + sticky toolbar + footer)
- Home card grid (sketch 001-D — warm hero + stat band + `№ 01 · Databases` card grid with rotating accent borders + dark CTA)
- Database editorial-row list (sketch 002-B — editorial full-width rows listing tables)
- Interaction tokens (0.15s transitions, translateY -2px hover, drop caps on article rows)

Phase 4 implements the home + database pages, using the sketch skill as the locked contract.

---

## Phase-4 Harvest Map

Every visual element this phase ships has a source in M1's existing implementation. The port is **structural** (Datasette Jinja → FastAPI Jinja), not a redesign.

| Output | Source (M1) | Notes |
|---|---|---|
| `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` | `templates/_header.html` + `templates/_footer.html` + site shell wiring | Combine into one base template with Jinja blocks (`{% block content %}`, `{% block head %}`) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/index.html` | `templates/index.html` | Port Jinja, adapt data-access contract (reads `databases` from route context, not Datasette's `{{ databases }}` built-in) |
| `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` | `templates/database.html` | Same pattern; adapt `{{ tables }}` variable assembly |
| `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` | `static/css/zeeker-base.css` (harvest only theme + shell + home + database sections) | Leave feed/row/aux sections for Phase 5-6 |
| `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/*.woff2` | `static/fonts/*.woff2` | Copy self-hosted Inter + JetBrains Mono + Fraunces files |

## Design deltas (Phase-4-specific)

Very few. The skill covers almost everything.

1. **Data-access contract change (not visible in rendered output):** frontend calls Datasette's JSON API and renders Jinja. M1 rendered inside Datasette's Jinja environment with direct access to Datasette's template variables (`databases`, `tables`, etc.). Post-port, these variables are populated by the FastAPI route handler, not Datasette. Template logic that previously accessed Datasette-specific builtins must be adapted. Example:
   - M1: `{% for name, info in databases.items() %}` where `databases` is Datasette's dict
   - Post-port: `{% for db in databases %}` where `databases` is a list of dicts assembled by the route handler
2. **Static-asset paths change:** M1 referenced `/static/css/zeeker-base.css` served by Datasette. Frontend serves `/static/css/zeeker.css` at the same URL path (Caddy catch-all routes `/static/*` to frontend; datasette no longer serves these paths).
3. **Font CDN refs:** none exist in M1 (already self-hosted per PROJECT.md). Preserve.
4. **Cache-Control headers on HTML:** M1 didn't set these explicitly (Datasette defaults). Frontend SHOULD add `Cache-Control: public, max-age=60, stale-while-revalidate=300` on `/` and `/{db}` responses.

## Out of scope for this UI-SPEC

- Table browse page layout (Phase 5 — sketch 004-A feed cards)
- Row view layout (Phase 5 — sketch 003 variants)
- Auxiliary page layouts (Phase 6)
- Any palette/typography/spacing/interaction changes vs the skill — if a harvest looks wrong, fix the harvest, not the design

---

## Acceptance Criteria

Visual parity with M1 — the rendered `/` and `/{db}` pages served from frontend MUST look identical to the M1-served versions (modulo the post-Caddy URL base, which was resolved in Phase 3's re-baselining).

Concrete checks:
- Homepage hero renders with Fraunces italic accent on the H1 `<em>` + petrol stat band below + card grid of databases with rotating accent border colors (ochre → terracotta → petrol cycle per nth-child)
- Database page renders with the hero + stat band + editorial-row table list (full-width rows, mono-font columns, right-aligned row counts, FTS badge where applicable)
- Shell chrome (dark nav + breadcrumb + footer) visible and styled correctly on both pages
- Self-hosted fonts load without CDN refs (Inter + JetBrains Mono + Fraunces — check `curl -I http://localhost/static/fonts/*.woff2`)
- `zeeker.css` loads from frontend path (`http://localhost/static/css/zeeker.css` — 200)
- No references to `/static/css/zeeker-base.css` (M1 path) in frontend-rendered HTML

Visual regression testing not in scope — M1's `scripts/visual_qa.py` is against Datasette-served templates; may adapt in Phase 6 or defer. Manual visual spot-check at the human checkpoint in Plan 04-05 (the deploy-and-verify plan) is the gate.

---

## References

- Design contract (primary): `.claude/skills/sketch-findings-zeeker-datasette/SKILL.md`
- Design sources: `.claude/skills/sketch-findings-zeeker-datasette/sources/`
- M1 artifacts: `templates/index.html`, `templates/database.html`, `static/css/zeeker-base.css`, `templates/_header.html`, `templates/_footer.html`, `static/fonts/`
- M1 completion: `.planning/phases/01-editorial-shell-home-inventory/` (each plan's SUMMARY.md documents what was built)

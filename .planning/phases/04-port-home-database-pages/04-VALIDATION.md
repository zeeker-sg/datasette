---
phase: 4
slug: port-home-database-pages
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-21
updated: 2026-04-22
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for the first user-visible FastAPI/Jinja port. Combines pytest (Jinja render + route contract via MockTransport), bash + curl (live routing + CSS/font serving + HTML structural assertions), and a final production smoke that authors may re-run on `data.zeeker.sg` (manual gate in Plan 04-05).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-httpx (frontend handlers + Jinja + datasette client mocks) + bash + curl (live routing + structural HTML) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` → `[tool.pytest.ini_options]` (added in Plan 04-01) |
| **Quick run command** | `bash scripts/verify_phase_04.sh` (added in Plan 04-05) |
| **Full suite command** | `bash scripts/verify_phase_04.sh && cd packages/zeeker-frontend && uv run pytest -q` |
| **Estimated runtime** | ~15 seconds (pytest ~3s, shell assertions ~10s) |

---

## Sampling Rate

- **After every task commit:** Run `bash scripts/verify_phase_04.sh` AND `cd packages/zeeker-frontend && uv run pytest -q`.
- **After every plan wave:** Full suite (verify_phase_04.sh + frontend pytest + Phase-3 parity wrap to confirm API unchanged).
- **Before `/gsd-verify-work`:** Full suite green + production smoke (Plan 04-05) + operator visual spot-check.
- **Max feedback latency:** 15 seconds (local); production smoke adds deploy roundtrip.

---

## Per-Task Verification Map

> Each task ID below references a concrete Task inside its PLAN. The 3 phase REQ-* IDs (REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http) are each covered by at least two tasks.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-T1 | 01 | 1 | REQ-frontend-data-via-http, REQ-eliminate-template-drift | T-04-01-02, T-04-01-04 | filters + httpx client with isolated `_zeeker_*`+hidden logic; Jinja2Templates autoescape default-on | pytest | `cd packages/zeeker-frontend && uv run pytest tests/test_filters.py tests/test_client.py -q` | ❌ W0 | ⬜ pending |
| 04-01-T2 | 01 | 1 | REQ-frontend-data-via-http | T-04-01-01, T-04-01-02, T-04-01-07 | Lifespan-scoped httpx + StaticFiles mount + Jinja2Templates with filters/globals registered; base.html self-contained (no datasette `default:` extends) | python-import smoke | `cd packages/zeeker-frontend && uv run python -c "from zeeker_frontend.main import app, templates; tmpl = templates.get_template('base.html'); rendered = tmpl.render({'request': None, 'current_year': 2026, 'metadata': {'title': 'test', 'menu_links': []}}); assert 'db-nav' in rendered and 'site-footer' in rendered and '/static/css/zeeker.css' in rendered; print('OK')"` | ❌ W0 | ⬜ pending |
| 04-02-T1 | 02 | 2 | REQ-eliminate-template-drift | T-04-02-01, T-04-02-03 | zeeker.css harvested = theme+shell+home+db subset of M1; 3 woff2 fonts copied byte-identically; no Phase-5 feed-card leak; no undefined `var(--foo)` | shell | `bash -c 'DST=packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css; test -f "$DST"; [ $(grep -c "{" "$DST") = $(grep -c "}" "$DST") ]; [ $(grep -c "@font-face" "$DST") = 3 ]; ! grep -q "va-feed" "$DST"; for f in inter-latin jetbrains-mono-latin fraunces-latin; do test -s "packages/zeeker-frontend/src/zeeker_frontend/static/fonts/$f.woff2"; done'` | ❌ W0 | ⬜ pending |
| 04-03-T1 | 03 | 3 | REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http | T-04-03-01, T-04-03-02, T-04-03-03, T-04-03-04 | GET / renders home HTML with db-statband + italic H1 + cards grid + zeeker.css ref; no zeeker-base.css leak; `*` wildcard filtered; 503 on datasette failure | pytest + shell | `cd packages/zeeker-frontend && uv run pytest tests/test_home.py -q && curl -fsS http://localhost/ \| grep -q 'db-statband' && curl -fsS http://localhost/ \| grep -qE '<h1>[^<]*<em' && ! curl -fsS http://localhost/ \| grep -q 'zeeker-base.css'` | ❌ W0 | ⬜ pending |
| 04-04-T1 | 04 | 3 | REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http | T-04-04-01, T-04-04-02, T-04-04-03, T-04-04-05 | GET /sglawwatch renders editorial-row list; hidden + FTS tables filtered via `hidden` flag (single predicate); 404 on unknown db; italic last-word H1 | pytest + shell | `cd packages/zeeker-frontend && uv run pytest tests/test_database.py -q && curl -fsS http://localhost/sglawwatch \| grep -q 'class=\"list\"' && ! curl -fsS http://localhost/sglawwatch \| grep -q '_zeeker' && ! curl -fsS http://localhost/sglawwatch \| grep -q 'headlines_fts' && [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost/nonexistent-db-check)" = "404" ]` | ❌ W0 | ⬜ pending |
| 04-05-T1 | 05 | 4 | REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http | T-04-05-01, T-04-05-02, T-04-05-03, T-04-05-04 | verify_phase_04.sh authored (delegates to verify_phase_03.sh); docker-compose.prod.yml + Caddyfile.prod validated; local verifier green | shell | `bash scripts/verify_phase_04.sh && docker run --rm -v "$PWD/Caddyfile.prod:/etc/caddy/Caddyfile:ro" caddy:2.11.2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && docker compose -f docker-compose.yml -f docker-compose.prod.yml config > /dev/null` | ❌ W0 | ⬜ pending |
| 04-05-T2 | 05 | 4 | REQ-frontend-route-set, REQ-eliminate-template-drift, REQ-frontend-data-via-http | T-04-05-01..08 | Production deploy succeeds; operator applies A/B/C/D triage; STATE/ROADMAP updated atomically; on ship: phase-04-pre baseline captured post-soak | manual + production smoke | `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh` (operator-executed) | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

Artifacts MUST exist before downstream waves can claim "done":

- [ ] `packages/zeeker-frontend/src/zeeker_frontend/filters.py` — Jinja custom filters + s/plural helpers (Plan 01)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py` — thin httpx wrapper + TTL cache (Plan 01)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html` — shared shell chrome (Plan 01)
- [ ] `packages/zeeker-frontend/pyproject.toml` — pytest-httpx + pytest-asyncio + [tool.pytest.ini_options] (Plan 01)
- [ ] `packages/zeeker-frontend/tests/conftest.py` — shared fixtures (Plan 01)
- [ ] `packages/zeeker-frontend/tests/fixtures/{databases,sglawwatch,metadata}.json` — captured from live datasette (Plan 01)
- [ ] `packages/zeeker-frontend/tests/test_filters.py` — 15+ unit tests (Plan 01)
- [ ] `packages/zeeker-frontend/tests/test_client.py` — MockTransport unit tests (Plan 01)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css` — harvested CSS ≥700 lines (Plan 02)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/static/fonts/{inter-latin,jetbrains-mono-latin,fraunces-latin}.woff2` — self-hosted fonts (Plan 02)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/routes_home.py` — GET / handler (Plan 03)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/templates/index.html` — home page template (Plan 03)
- [ ] `packages/zeeker-frontend/tests/test_home.py` — 5 route tests (Plan 03)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/routes_database.py` — GET /{db} handler (Plan 04)
- [ ] `packages/zeeker-frontend/src/zeeker_frontend/templates/database.html` — database page template (Plan 04)
- [ ] `packages/zeeker-frontend/tests/test_database.py` — 7 route tests (Plan 04)
- [ ] `scripts/verify_phase_04.sh` — structural HTML + live routing assertions (Plan 05)
- [ ] `docker-compose.prod.yml` — production overlay (Plan 05)
- [ ] `Caddyfile.prod` — production Caddyfile with auto-HTTPS for data.zeeker.sg (Plan 05)
- [ ] `.planning/phases/04-port-home-database-pages/04-05-DEPLOY.md` — runbook (Plan 05)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual parity with M1: homepage and database page look identical to the M1 versions (palette, typography, card accent rotation, stat band proportions) | REQ-eliminate-template-drift | Pixel-perfect parity can't be automated without visual regression tooling (scripts/visual_qa.py is against datasette templates, not frontend) | Open `http://localhost/` and `http://localhost/sglawwatch` in a browser hard-refreshed (Cmd-Shift-R). Compare against a pre-port screenshot from M1. Document outcome in `04-05-SUMMARY.md`. |
| Production smoke on `https://data.zeeker.sg` | All three phase REQs | Production-only; TLS handshake + CDN caching + real user agents can surface issues that localhost doesn't | After Plan 04-05 deploy: `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_04.sh` + browser visual. Document in `04-05-SUMMARY.md`. |
| Four-category triage decision (A/B/C/D) | Phase gate | Judgment call involving business risk, not an automatable check | Operator at Plan 04-05 Task 2 checkpoint responds `approved` / `approved with notes` / `rollback: <desc>`. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (all 7 task IDs have automated checks above)
- [x] Wave 0 covers all MISSING references (client/filters/tests/CSS harvest/templates/verifier/prod compose)
- [x] No watch-mode flags (pytest runs single-pass via `-q`)
- [x] Feedback latency < 15s local; prod smoke separate
- [x] `nyquist_compliant: true` — Per-Task Verification Map populated with actual task IDs

**Approval:** planned — ready for `/gsd-execute-phase 04`

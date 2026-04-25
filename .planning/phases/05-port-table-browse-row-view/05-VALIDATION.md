---
phase: 5
slug: port-table-browse-row-view
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Detailed test pyramid lives in `05-RESEARCH.md` `## Validation Architecture` section.
> This file is the contract; the planner attaches each task to a row in the verification map below.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing in `packages/zeeker-frontend/`) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` (carry-forward from Phase 4) |
| **Quick run command** | `cd packages/zeeker-frontend && uv run pytest -x -q` |
| **Full suite command** | `cd packages/zeeker-frontend && uv run pytest -v` |
| **Verifier (E2E)** | `bash scripts/verify_phase_05.sh` (requires running stack — `docker compose up -d` first) |
| **Estimated runtime** | unit + integration ~6s; full suite + verifier ~25s |

---

## Sampling Rate

- **After every task commit:** Run `cd packages/zeeker-frontend && uv run pytest -x -q`
- **After every plan wave:** Run full suite `cd packages/zeeker-frontend && uv run pytest -v`
- **Before `/gsd-verify-work`:** Full suite green AND `verify_phase_05.sh` exits 0
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

The planner is responsible for filling this table — one row per task in every PLAN.md.
Each task either has an automated verify command or a Wave 0 dependency that adds one.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _to be filled by planner_ |  |  |  |  |  |  |  |  | ⬜ pending |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Coverage rule:** every REQ-ID claimed by any plan in this phase must have at least
one row above with a non-empty `Automated Command`. The plan-checker enforces this.

---

## Wave 0 Requirements

The planner declares Wave 0 in plan 05-01 (or earliest plan). Expected stubs:

- [ ] `packages/zeeker-frontend/tests/test_routes_table.py` — REQ-frontend-route-set, REQ-frontend-data-via-http
- [ ] `packages/zeeker-frontend/tests/test_routes_row.py` — REQ-frontend-route-set
- [ ] `packages/zeeker-frontend/tests/test_datasette_client_table_row.py` — extends Phase 4 `test_datasette_client.py` for `fetch_table` / `fetch_row`
- [ ] `packages/zeeker-frontend/tests/test_urls.py` — querystring helpers (sort toggle, facet add/remove, page-size, tilde-encode for compound PKs)
- [ ] `packages/zeeker-frontend/tests/conftest.py` — shared MockTransport JSON fixtures (carry-forward; extend with table+row payloads)
- [ ] `scripts/verify_phase_05.sh` — E2E verifier mirroring `verify_phase_04.sh` (positive + negative + Phase-6 boundary asserts)

*pytest framework is already installed (Phase 4) — no install task needed.*

---

## Test Pyramid (summary; see RESEARCH.md `## Validation Architecture` for full detail)

**Layer 1 — Unit (fastest, deterministic, no IO):**
- `urls.py` querystring helpers — sort toggle, facet add/remove, page-size, tilde-encode compound PK, querystring allowlist (rejects `_extras=`, etc.)
- `datasette_client.fetch_table` and `fetch_row` — MockTransport-backed httpx client; assert `?_shape=objects` is requested, `next_url` host/path is rewritten, 404→`None`, 5xx→`HTTPException(503)`
- Template-rendering unit tests — render `table.html` and `row.html` with a synthetic context dict; assert structural elements per UI-SPEC

**Layer 2 — Integration (ASGI-level, real router, mocked datasette):**
- `httpx.AsyncClient` against the FastAPI app via `ASGITransport`, with `app.state.http` swapped to a MockTransport-backed httpx client
- For each layout mode (feed / tabular / longform-list / article / judgment / longform / row tabular), assert the rendered HTML contains the layout-specific class names from UI-SPEC
- Assert `Cache-Control: public, max-age=60, stale-while-revalidate=300` on both routes
- Assert `_zeeker_*` views, hidden tables, and unmapped `display.*` modes resolve to safe fallbacks
- Assert export anchors render with the expected `/{db}/{table}.csv?...` and `.json?...` hrefs and DO NOT enter the frontend (no handler invoked for those paths in tests)

**Layer 3 — E2E verifier (`scripts/verify_phase_05.sh`):**
- Positive structural asserts on `/{db}/{table}` and `/{db}/{table}/{pk}` for sample tables (sglawwatch.headlines, Zeeker-Judgements.judgments, sg-gov-newsrooms `*_news`)
- Export link href correctness + Caddy suffix-routes to datasette (compare bytes of `/{db}/{table}.csv` from frontend vs datasette directly)
- Negative asserts: `_zeeker_*` does not leak; `/{db}/{table}/{pk}/some-nested-path` returns 404
- Phase-6 boundary: `/-/sql`, `/-/search`, `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt` all return 404 from frontend (NOT mounted)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual fidelity to sketch 003-A / 003-B / 004-A | UI-SPEC | Pixel/typography parity needs human eye | After deploy: visit the three reference tables (`sglawwatch/headlines`, `Zeeker-Judgements/judgments`, `sglawwatch/about_singapore_law`), compare against `.claude/skills/sketch-findings-zeeker-datasette/references/*.md` |
| FTS `<mark>` policy | UI-SPEC § FTS search | Datasette 0.65.x doesn't expose `_search_highlight` (RESEARCH pitfall #3) — final policy needs human signoff | Plan 05-02 must document the chosen policy (skip-in-v1 recommended); reviewer confirms before merge |
| Drop cap suppression on short bodies | UI-SPEC § row_mode: article | Heuristic-based (≥ 3 paragraphs) — visual check | Open an article-mode row with a short body and confirm no drop cap renders |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or a Wave 0 dependency that creates one
- [ ] Sampling continuity: no 3 consecutive tasks in any plan without an automated verify
- [ ] Wave 0 covers all MISSING references in the verification map
- [ ] No watch-mode flags in any test command
- [ ] Feedback latency < 30s on the quick-run command
- [ ] `verify_phase_05.sh` is added to `scripts/` and runs in the verifier-script section
- [ ] `nyquist_compliant: true` set in frontmatter once map is fully populated

**Approval:** pending

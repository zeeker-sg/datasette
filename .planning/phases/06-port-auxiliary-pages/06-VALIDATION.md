---
phase: 6
slug: port-auxiliary-pages
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 + pytest-asyncio 1.3.0 + pytest-httpx 0.36.0 (already pinned in `packages/zeeker-frontend/pyproject.toml`) |
| **Config file** | `packages/zeeker-frontend/pyproject.toml` `[tool.pytest.ini_options] asyncio_mode = "auto"` |
| **Quick run command** | `cd packages/zeeker-frontend && uv run pytest -x` |
| **Full suite command** | `cd packages/zeeker-frontend && uv run pytest && bash scripts/verify_phase_06.sh && bash scripts/verify_api_parity.sh` |
| **Estimated runtime** | ~10 seconds (pytest) + ~15 seconds (integration verifier) |

---

## Sampling Rate

- **After every task commit:** Run `cd packages/zeeker-frontend && uv run pytest -x`
- **After every plan wave:** Run `cd packages/zeeker-frontend && uv run pytest -x` + targeted verifier section
- **Before `/gsd-verify-work`:** Full suite must be green: `cd packages/zeeker-frontend && uv run pytest && bash scripts/verify_phase_06.sh && bash scripts/verify_api_parity.sh`
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 6-01-* | 01 (Wave 0) | 0 | REQ-frontend-route-set | T-input-validation | Test fixtures + verifier scaffold installed | infra | `cd packages/zeeker-frontend && uv run pytest --collect-only` | ❌ W0 | ⬜ pending |
| 6-02-* | 02 | 1 | REQ-frontend-data-via-http | T-ssrf, T-info-disclosure | Querystring allowlist on `_param_*`; FTS discovery hides `_zeeker_*` and `hidden:true` | unit | `cd packages/zeeker-frontend && uv run pytest tests/test_datasette_client_phase06.py -x` | ❌ W0 | ⬜ pending |
| 6-03-* | 03 | 1 | REQ-frontend-route-set, REQ-eliminate-template-drift | T-xss, T-info-disclosure | Jinja autoescape on echoed query strings; no `zeeker-datasette:8001` leak | unit | `cd packages/zeeker-frontend && uv run pytest tests/test_routes_aux.py -x` | ❌ W0 | ⬜ pending |
| 6-04-* | 04 | 2 | REQ-frontend-route-set | T-xss, T-partial-failure | `<mark>` only via Datasette `_search_highlight`; partial failures isolated via `gather(return_exceptions=True)` | unit | `cd packages/zeeker-frontend && uv run pytest tests/test_routes_search.py -x` | ❌ W0 | ⬜ pending |
| 6-05-* | 05 | 2 | REQ-frontend-route-set | T-sql-injection, T-dos-ms-limit, T-info-disclosure | Datasette `_param_<name>` binding; trust ms_limit; truncated=true banner | unit | `cd packages/zeeker-frontend && uv run pytest tests/test_routes_sql.py -x` | ❌ W0 | ⬜ pending |
| 6-06-* | 06 | 3 | REQ-eliminate-template-drift, REQ-api-byte-parity | T-template-drift | CSS append-only; nav re-pointed; verifier flips Phase-5 boundary asserts | integration | `bash scripts/verify_phase_06.sh && bash scripts/verify_api_parity.sh` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Per-task entries are placeholders pending plan task IDs from gsd-planner. The Plan column will be re-numbered by the planner; the Wave column reflects the planner's wave assignment after planning completes.*

---

## Wave 0 Requirements

- [ ] `packages/zeeker-frontend/tests/test_routes_aux.py` — stubs for REQ-frontend-route-set covering `/developers`, `/status`, `/sources`, `/about`, `/how-to-use`, `/llms.txt`, `/robots.txt`
- [ ] `packages/zeeker-frontend/tests/test_routes_search.py` — stubs for `/search` State A + State B + partial-failure + 503 empty-cache
- [ ] `packages/zeeker-frontend/tests/test_routes_sql.py` — stubs for `/sql` landing, `GET /sql/{db}`, `POST /sql/{db}` success/error/truncation, `_detect_params` regex
- [ ] `packages/zeeker-frontend/tests/test_datasette_client_phase06.py` — stubs for `discover_searchable_tables`, `search_table`, `execute_sql`
- [ ] `packages/zeeker-frontend/tests/test_changelog.py` — stubs for YAML loader + empty-list fallback
- [ ] `packages/zeeker-frontend/tests/fixtures/searchable_databases.json` — fixture for FTS fan-out tests
- [ ] `packages/zeeker-frontend/tests/fixtures/headlines_search_results.json` — fixture for FTS row results
- [ ] `packages/zeeker-frontend/tests/fixtures/metadata_with_canned_queries.json` — fixture for canned-queries listing
- [ ] `packages/zeeker-frontend/tests/fixtures/sql_error_400.json` — captured Datasette 400 body shape
- [ ] `scripts/verify_phase_06.sh` — integration verifier scaffold (extends Phase 5; flips boundary asserts)

*No new framework install required — pytest, pytest-asyncio, pytest-httpx already pinned.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Production smoke against `https://data.zeeker.sg` | REQ-frontend-route-set, REQ-eliminate-template-drift | Production deploy is gated; smoke after deploy | `BASE_URL=https://data.zeeker.sg bash scripts/verify_phase_06.sh` |
| `/-/search` and `/-/sql` still served by datasette (not frontend) | D-01, D-02 (routing seam) | Requires running both containers behind Caddy | `curl -sS http://localhost/-/search?q=test \| grep -i datasette` |
| Visual check of italic-accent H1 + civic-broadsheet palette on every aux page | REQ-eliminate-template-drift, UI-SPEC | Subjective design review | Visit each route in browser; confirm H1 has italic `<em>`, palette matches sketch findings, footer year is 2026 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

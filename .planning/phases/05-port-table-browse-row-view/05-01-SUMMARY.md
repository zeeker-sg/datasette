---
phase: 05-port-table-browse-row-view
plan: "01"
subsystem: zeeker-frontend
tags: [datasette-client, url-helpers, routing, fixtures, tdd]
dependency_graph:
  requires: [04-04]
  provides: [fetch_table, fetch_row, urls.py, routes_table stub, routes_row stub, Wave-0 fixtures]
  affects: [05-02, 05-03]
tech_stack:
  added: [urls.py (pure-function querystring helpers)]
  patterns: [MockTransport unit tests, frozenset allowlist, tilde-encode port]
key_files:
  created:
    - packages/zeeker-frontend/src/zeeker_frontend/urls.py
    - packages/zeeker-frontend/src/zeeker_frontend/routes_table.py
    - packages/zeeker-frontend/src/zeeker_frontend/routes_row.py
    - packages/zeeker-frontend/tests/test_urls.py
    - packages/zeeker-frontend/tests/test_datasette_client_table_row.py
    - packages/zeeker-frontend/tests/fixtures/headlines_table.json
    - packages/zeeker-frontend/tests/fixtures/about_singapore_law_table.json
    - packages/zeeker-frontend/tests/fixtures/headlines_row.json
    - packages/zeeker-frontend/tests/fixtures/judgments_row.json
  modified:
    - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py
    - packages/zeeker-frontend/src/zeeker_frontend/main.py
    - packages/zeeker-frontend/tests/conftest.py
decisions:
  - "urls.py uses stdlib parse_qsl/urlencode (not MultiDict) — validated equivalent for all helpers"
  - "fetch_table allowlist via _TABLE_ALLOWED_PARAMS frozenset + column__operator pattern + non-underscore passthrough"
  - "Router registration order: home → database → table → row (specificity-correct)"
  - "Stub routes return 501 (not 404) so hidden-table guard behavior is distinguishable during dev"
metrics:
  duration: "4 minutes"
  completed: "2026-04-25T07:26:59Z"
  tasks_completed: 4
  files_changed: 13
---

# Phase 05 Plan 01: Foundation — datasette client, URL helpers, router stubs Summary

Wave-1 foundation plan: extends the datasette HTTP client with fetch_table/fetch_row, ports datasette's querystring helpers to urls.py, creates stub route handlers with the hidden-table guard, registers them in main.py, and ships Wave-0 test fixtures + helper unit tests so Plans 05-02/05-03 can drop straight in.

## What Was Built

### Task 1 — Wave-0 Test Fixtures + conftest.py (commit 1b55e79)

Four JSON fixture files created from baseline captures:

**`tests/fixtures/headlines_table.json`**
- 10 rows in objects shape (keyed by column names, NOT list-of-lists)
- Columns: `id`, `category`, `title`, `source_link`, `author`, `date`, `summary`, `text`, `imported_on`
- `primary_keys: ["id"]`
- `facet_results.category` with 2 results (Straits Times: 6, Business Times: 4)
- `next_url` pointing to internal `zeeker-datasette:8001` hostname (handler rewrites in 05-02)
- Constructed by transforming `.planning/baselines/phase-03-pre/sglawwatch_headlines.json__size_10.json` rows from list-of-lists to list-of-dicts

**`tests/fixtures/about_singapore_law_table.json`**
- 10 rows in objects shape
- `primary_keys: []` (load-bearing rowid-fallback assertion for Pitfall 4 testing)
- `columns[0] == "rowid"` — confirmed from baseline
- `facet_results: {}`, `next_url: null`

**`tests/fixtures/headlines_row.json`**
- Single-element `rows` list (first row from headlines)
- `primary_keys: ["id"]`, `primary_key_values: ["fdd3ea972982da1e8326e4233586bd8e"]`

**`tests/fixtures/judgments_row.json`**
- Synthetic (no captured baseline for Zeeker-Judgements)
- Keys: `case_name`, `court`, `citation`, `decision_date`, `text`, `subject_tags`, `source_url`
- `primary_keys: []`, rowid-based

**`tests/conftest.py` additions:**
```python
@pytest.fixture
def headlines_table_fixture() -> dict:
    return _load_fixture("headlines_table.json")

@pytest.fixture
def about_singapore_law_table_fixture() -> dict:
    return _load_fixture("about_singapore_law_table.json")

@pytest.fixture
def headlines_row_fixture() -> dict:
    return _load_fixture("headlines_row.json")

@pytest.fixture
def judgments_row_fixture() -> dict:
    return _load_fixture("judgments_row.json")
```

All existing fixtures untouched.

---

### Task 2 — urls.py + test_urls.py (commit 073da93)

**`src/zeeker_frontend/urls.py`** — 9 public helper functions:

```python
def path_with_added_args(path: str, query_string: str, args) -> str
def path_with_replaced_args(path: str, query_string: str, args) -> str
def path_with_removed_args(path: str, query_string: str, keys) -> str
def toggle_facet_value(path: str, qs: str, col: str, val: str) -> str
def clear_facet_value(path: str, qs: str, col: str, val: str) -> str
def set_sort(path: str, qs: str, col: str, current_state: str | None) -> str
def export_url(db: str, table: str, ext: str, query_string: str) -> str
def tilde_encode(s: str) -> str
def row_url(db: str, table: str, pk_values) -> str | None
```

Key contracts verified:
- `tilde_encode("a/b")` → `"a~2Fb"` (Pitfall 5)
- `row_url("db", "tbl", [])` → `None` (Pitfall 4)
- `set_sort("/p", "", "date", None)` → `"/p?_sort=date"` (unsorted→asc cycle start)

**`tests/test_urls.py`**: 30 tests, all green. Class-per-function grouping per test_filters.py style.

---

### Task 3 — datasette_client.py extension + test_datasette_client_table_row.py (commit 336ce24)

**New in `datasette_client.py`:**

```python
_TABLE_ALLOWED_PARAMS = frozenset({
    "_size", "_sort", "_sort_desc", "_search", "_next",
    "_facet", "_facet_array", "_facet_date",
})

async def fetch_table(client, db, table, params=None) -> dict | None
async def fetch_row(client, db, table, pk) -> dict | None
```

Allowlist logic (T-05-02 mitigation):
- Keys in `_TABLE_ALLOWED_PARAMS` → forwarded
- Keys containing `__` (column__operator) → forwarded
- Keys not starting with `_` (plain column names) → forwarded
- Everything else (e.g. `_extras`, `_internal`, `allow_execute_sql`) → silently dropped

Both functions:
- Always send `_shape=objects` (Pitfall 1 — force row-as-dict shape)
- Return `None` on 404 (before `raise_for_status()`)
- Raise `httpx.HTTPError` on other non-2xx

**`tests/test_datasette_client_table_row.py`**: 12 tests, all green. MockTransport-driven, no FastAPI app.

---

### Task 4 — Stub routes + main.py wiring (commit 4c72a8f)

**`routes_table.py`**:
```python
router = APIRouter()
_HIDDEN_TABLE_PREFIXES = ("_zeeker",)
_HIDDEN_TABLE_SUFFIXES = ("_fts", "_fts_data", "_fts_idx", "_fts_docsize", "_fts_config")

@router.get("/{db}/{table}", response_class=HTMLResponse)
async def table_page(request: Request, db: str, table: str):
    if table.startswith(_HIDDEN_TABLE_PREFIXES) or table.endswith(_HIDDEN_TABLE_SUFFIXES):
        raise HTTPException(status_code=404, detail="Table not found")
    raise HTTPException(status_code=501, detail="Not implemented — Plan 05-02 fills this in")
```

**`routes_row.py`**: same guard pattern for `/{db}/{table}/{pk}`.

**`main.py` additions:**

Jinja globals registration (after `templates.env.globals["plural"] = zfilters.plural`):
```python
from zeeker_frontend import urls as zurls
templates.env.globals["path_with_added_args"] = zurls.path_with_added_args
templates.env.globals["path_with_replaced_args"] = zurls.path_with_replaced_args
templates.env.globals["path_with_removed_args"] = zurls.path_with_removed_args
templates.env.globals["toggle_facet_value"] = zurls.toggle_facet_value
templates.env.globals["clear_facet_value"] = zurls.clear_facet_value
templates.env.globals["set_sort"] = zurls.set_sort
templates.env.globals["export_url"] = zurls.export_url
templates.env.globals["row_url"] = zurls.row_url
templates.env.globals["tilde_encode"] = zurls.tilde_encode
```

Router registration (specificity order):
```
line 116: app.include_router(home_router)
line 117: app.include_router(database_router)
line 118: app.include_router(table_router)
line 119: app.include_router(row_router)
```

**ASGI smoke test output:**
```
('/sglawwatch/_zeeker_schemas', '/sglawwatch/headlines_fts', '/sglawwatch/some_fts_data', '/sglawwatch/headlines')
→ (404, 404, 404, 501)
```

Hidden-table guard active; visible table returns 501 (stub, replaced by 05-02).

---

## Test Results

Full suite after this plan: **83 tests, 0 failures**

Breakdown:
- test_filters.py: existing (carried forward)
- test_home.py: existing (carried forward)
- test_database.py: existing (carried forward)
- test_urls.py: 30 new tests
- test_datasette_client_table_row.py: 12 new tests

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Threat Mitigations Applied

| Threat ID | Status |
|-----------|--------|
| T-05-01 (path traversal) | datasette authoritative; fetch_table/fetch_row return None on 404 |
| T-05-02 (querystring smuggling) | _TABLE_ALLOWED_PARAMS frozenset + allowlist logic in fetch_table |
| T-05-03 (hidden table access) | prefix+suffix guard at route boundary in both stub handlers |
| T-05-04 (XSS) | carried forward from Phase 4; Jinja autoescape ON; no |safe on data |
| T-05-05 (open redirect) | not yet exercised (no next_url in stubs); Plan 05-02 handles |
| T-05-06 (cache poisoning) | accepted; HTML-only responses in Phase 5 |

---

## Self-Check

### Files exist:
- [x] packages/zeeker-frontend/src/zeeker_frontend/urls.py
- [x] packages/zeeker-frontend/src/zeeker_frontend/routes_table.py
- [x] packages/zeeker-frontend/src/zeeker_frontend/routes_row.py
- [x] packages/zeeker-frontend/tests/test_urls.py
- [x] packages/zeeker-frontend/tests/test_datasette_client_table_row.py
- [x] packages/zeeker-frontend/tests/fixtures/headlines_table.json
- [x] packages/zeeker-frontend/tests/fixtures/about_singapore_law_table.json
- [x] packages/zeeker-frontend/tests/fixtures/headlines_row.json
- [x] packages/zeeker-frontend/tests/fixtures/judgments_row.json

### Commits exist:
- [x] 1b55e79 — Task 1 (fixtures + conftest)
- [x] 073da93 — Task 2 (urls.py + test_urls.py)
- [x] 336ce24 — Task 3 (datasette_client extension + tests)
- [x] 4c72a8f — Task 4 (stub routes + main.py)

## Self-Check: PASSED

---
phase: 05-port-table-browse-row-view
reviewed: 2026-04-25T11:35:04Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - metadata.json
  - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py
  - packages/zeeker-frontend/src/zeeker_frontend/main.py
  - packages/zeeker-frontend/src/zeeker_frontend/routes_row.py
  - packages/zeeker-frontend/src/zeeker_frontend/routes_table.py
  - packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/applied_facets.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/facet_sidebar.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/pagination.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_article.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_judgment.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_longform.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_tabular.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_feed.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_longform_list.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/table_tabular.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/row.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/table.html
  - packages/zeeker-frontend/src/zeeker_frontend/urls.py
  - packages/zeeker-frontend/tests/conftest.py
  - packages/zeeker-frontend/tests/fixtures/about_singapore_law_table.json
  - packages/zeeker-frontend/tests/fixtures/headlines_row.json
  - packages/zeeker-frontend/tests/fixtures/headlines_table.json
  - packages/zeeker-frontend/tests/fixtures/judgments_row.json
  - packages/zeeker-frontend/tests/test_datasette_client_table_row.py
  - packages/zeeker-frontend/tests/test_routes_row.py
  - packages/zeeker-frontend/tests/test_routes_table.py
  - packages/zeeker-frontend/tests/test_urls.py
  - scripts/verify_phase_05.sh
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-25T11:35:04Z
**Depth:** standard
**Files Reviewed:** 27 (29 paths in scope; 2 are .json fixture data not code-reviewed for findings)
**Status:** issues_found

## Summary

Phase 5 ports Datasette's table-browse and row-view templates onto the FastAPI/Jinja frontend. The handlers (`routes_table.py`, `routes_row.py`) follow the design contracts: hidden-table guard with same-wording 404, `httpx.HTTPError` → 503, `_shape=objects` always, querystring allowlist enforced inside `fetch_table`, `next_url` rewritten to drop the internal hostname, and `Cache-Control: max-age=60, stale-while-revalidate=300` on both routes. `urls.py` is a clean pure-function port of the datasette helpers. Jinja autoescape is on (Starlette `Jinja2Templates`), and none of the new partials apply `|safe` to user content — the only `|safe` calls in the codebase are on hard-coded `s()` strings in `index.html`, which is out of scope.

No **Critical** issues found. The findings below are **Warnings** (correctness/robustness) and **Info** (maintainability). The most material warning is **WR-01**: `dict(request.query_params)` collapses multi-valued query keys (e.g. `_facet=category&_facet=date`), so multi-faceted requests forward only the last value to upstream — a feature regression vs. Datasette behavior, not a security bug. WR-02 and WR-03 cover smaller robustness gaps (`pk` not URL-encoded into the upstream path; pagination's `_size` detection uses substring match).

## Warnings

### WR-01: `dict(request.query_params)` drops repeated keys before forwarding to datasette

**File:** `packages/zeeker-frontend/src/zeeker_frontend/routes_table.py:37`
**Issue:** Starlette's `QueryParams` supports repeated keys, but converting via `dict(request.query_params)` keeps only the last value per key. For Phase-5 endpoints this silently breaks multi-valued params that Datasette accepts and that the allowlist explicitly permits — most notably `_facet`/`_facet_array`/`_facet_date` (a single page may pass `?_facet=category&_facet=date`) and any column filter where the user wants OR-style multi-select (`?category=A&category=B`). All but the last value is dropped before `fetch_table` ever sees them. The same `dict()` call is reused on line 64 for sort detection (which only reads `_sort`/`_sort_desc`, so no harm there), but the line-37 forward to upstream is the load-bearing one. `applied_filters` on line 73 already uses `multi_items()` correctly, which proves the team knows the right API — the upstream forward just missed it.
**Fix:** Forward multi-items as a list of pairs and adjust `fetch_table` to accept that shape (already trivial since `httpx.AsyncClient.get(..., params=...)` accepts `list[tuple[str, str]]`):

```python
# routes_table.py
multi_params = list(request.query_params.multi_items())
try:
    payload = await fetch_table(client, db, table, multi_params)
...
```

```python
# datasette_client.py — fetch_table()
def _allowed(k: str) -> bool:
    return (k in _TABLE_ALLOWED_PARAMS) or ("__" in k) or (not k.startswith("_"))

safe_pairs: list[tuple[str, Any]] = [("_shape", "objects")]
for k, v in (params or []):  # accept list[tuple] OR dict.items()
    if _allowed(k):
        safe_pairs.append((k, v))
r = await client.get(f"/{db}/{table}.json", params=safe_pairs)
```

A regression test: `await client_table.get("/sglawwatch/headlines?_facet=category&_facet=date")` → assert both facet names are present in the upstream-call capture.

### WR-02: `pk` path segment forwarded to upstream without URL-encoding

**File:** `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py:109`
**Issue:** `fetch_row` does `f"/{db}/{table}/{pk}.json"` — the `pk` value is whatever FastAPI captured from the URL path. FastAPI's path-parameter capture decodes percent-escapes, so a request like `/db/tbl/abc%23frag` arrives with `pk = "abc#frag"`. `httpx` then re-encodes most unreserved characters but treats `#` as a fragment delimiter when it appears in an f-string concatenation — i.e., the request goes out to `/db/tbl/abc.json` with fragment `frag`, returning a 404 from a different row (or the table page) instead of "row not found." Same hazard for `?` (becomes a query) and stray spaces. The blast-radius is small (frontend-internal, not exploitable beyond a confusing 404), but the symptom is genuinely confusing during debugging.
**Fix:** Build the URL via httpx's path encoding or call `urls.tilde_encode` on the segment so the upstream URL matches what Datasette routed in the first place:

```python
from urllib.parse import quote

async def fetch_row(client, db, table, pk):
    safe_pk = quote(pk, safe="")
    r = await client.get(f"/{db}/{table}/{safe_pk}.json", params={"_shape": "objects"})
```

Add a unit test: `pk="abc#frag"` → captured request path is `/db/tbl/abc%23frag.json`.

### WR-03: Pagination `_size` detection uses substring `in` — false positives possible

**File:** `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/pagination.html:14`
**Issue:** `('_size=' ~ n|string) in (request_qs|string)` is a substring search. For `n=50` this returns true on any querystring that *contains* the literal `_size=50` anywhere — including `_size=500` (`_size=50` is a prefix), or a column filter like `note=_size=50_special` (theoretical but legal). The first case is the realistic one: if a future plan adds a 500-row option or a user hits `?_size=500` manually, the row will both highlight 50 *and* still link 100 (because `_size=100` is not a substring of `_size=500`), producing a confusing inconsistent UI state.
**Fix:** Compare against the parsed value rather than the raw QS. Either pass `current_size` from the route handler (cleanest), or use the helper that already exists:

```jinja
{% set current_size = (request_qs|string).split('_size=')[1].split('&')[0] if '_size=' in (request_qs|string) else '' %}
{% if current_size == n|string %} ... {% endif %}
```

Or — preferred — set `current_size` in the route context and just compare ints:

```python
# routes_table.py
"current_size": int(qp.get("_size", 0)) or None,
```

```jinja
{% if current_size == n %} ... {% endif %}
```

### WR-04: Article/longform/judgment partials trust upstream `body` HTML when `striptags` returns to the page wrapped in `<p>` tags

**File:**
- `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_article.html:14-20`
- `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_longform.html:10-16`
- `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/row_judgment.html:26-33`

**Issue:** Not an XSS bug — Jinja autoescape is on, `striptags` removes `<…>`, and the `{{ para.strip() }}` interpolation is escaped. The flag is robustness: `striptags` is *not* an HTML sanitizer; it is regex-grade and known to mishandle certain malformed inputs (unbalanced `<`, comments containing `>`). If upstream `body` ever contained literal `<` from user content (say, a quote-stripped JSON-encoded snippet), `striptags` may eat surrounding text. This is a quality concern not a security one — autoescape on the result is the actual safety boundary, and it is in place. Worth noting because the comment in `row_judgment.html:39` ("split safely") suggests the team thinks of `striptags` + `replace` as sanitation.
**Fix:** Document in a comment that XSS safety comes from autoescape, not `striptags`. No code change needed unless a future template emits the body via `|safe`. If/when richer HTML rendering is introduced, switch to `bleach` with an allowlist.

### WR-05: `applied_filters` includes pagination cursors and any underscore-stripped param the user supplies

**File:** `packages/zeeker-frontend/src/zeeker_frontend/routes_table.py:73-76`
**Issue:** The filter `(k, v) for k, v in request.query_params.multi_items() if not k.startswith("_")` correctly excludes datasette internals. But it accepts *any* non-underscore key as a "column filter" and renders it as a removable chip in `applied_facets.html`. A request like `/sglawwatch/headlines?foo=bar&xss=<script>` (where `xss` is not a real column) renders `foo: bar ×` and `xss: <script> ×` chips. Autoescape neutralises the XSS, but the user sees nonsense column-name chips for any junk param. More concretely: forms or copy-paste links can carry analytics params (`utm_source`, `gclid`) that will appear as filter chips.
**Fix:** Cross-reference against `payload.get("columns")` before showing as a chip:

```python
columns_set = set(payload.get("columns") or [])
applied_filters = [
    (k, v) for k, v in request.query_params.multi_items()
    if not k.startswith("_") and (k.split("__", 1)[0] in columns_set)
]
```

This also stops `?utm_source=foo` from rendering a chip while still preserving column-with-operator filters like `date__gte`.

## Info

### IN-01: `_db_title` is duplicated verbatim across `routes_table.py` and `routes_row.py`

**File:** `packages/zeeker-frontend/src/zeeker_frontend/routes_table.py:22-24` and `routes_row.py:22-24`
**Issue:** Identical helper. Will drift.
**Fix:** Move to `zeeker_frontend.datasette_client` (or a new `zeeker_frontend.metadata`) and import in both routers.

### IN-02: `_HIDDEN_TABLE_PREFIXES` / `_HIDDEN_TABLE_SUFFIXES` are duplicated in both route modules

**File:** `routes_table.py:16-19`, `routes_row.py:14-18`
**Issue:** Same list, two copies. The hidden-table guard is a security-adjacent control — a single source of truth reduces the risk of one route updating the list and the other not. The current values look correct (FTS suffix list matches SQLite's `_fts`/`_fts_data`/`_fts_idx`/`_fts_docsize`/`_fts_config`); no bypass found, including for compound names like `tbl__fts` (substring) or `tbl_FTS` (case — SQLite is case-sensitive on table names, and Datasette routes preserve case, so the lowercase-only check is consistent with Datasette's own naming).
**Fix:** Define once in `zeeker_frontend.datasette_client` (or `metadata.py`), import from both. Add a tiny `is_hidden_table(name) -> bool` helper.

### IN-03: `_PK_DISPLAY_MAX = 12` truncates by character count, not codepoint width or bytes

**File:** `packages/zeeker-frontend/src/zeeker_frontend/routes_row.py:19, 27-30`
**Issue:** `pk[:n]` is character-count truncation. For ASCII PKs (UUIDs, sha hashes, integers) this is exactly right — no XSS, no surrogate split, autoescape handles the displayed output. For wide-grapheme PKs (e.g. an emoji or combining-mark composite key) the visual width differs from the count, but no codepoint can be split mid-byte because we slice the `str` not the bytes. Not a bug. Mentioned only because the review checklist asked: "bytes vs chars?" — this is char-correct. If a future feature adds per-database PK metadata (e.g. "PKs may contain CJK; render with `…`"), reconsider.
**Fix:** None required. Optionally move the constant to module-level config and add a docstring explaining it's char-count not byte-count.

### IN-04: `tilde_encode` reimplements percent encoding; could share `quote(s, safe="-._")`

**File:** `packages/zeeker-frontend/src/zeeker_frontend/urls.py:88-101`
**Issue:** Datasette's tilde-encoding intentionally diverges from RFC-3986 percent-encoding in two ways: it uses `~` instead of `%` (so the encoded form survives clean inside a URL path without re-encoding), and the SAFE set is fixed. The current implementation is byte-correct (matches Datasette's `utils/__init__.py:1173-1186` per the docstring) and the unit tests in `test_urls.py:102-120` cover the edge cases (Unicode, slash, percent). Just noting that this is intentional divergence, not a bug — kept for parity with Datasette URL contract.
**Fix:** Consider adding a comment that links to the upstream Datasette source line range so future maintainers don't "fix" this to use stdlib `quote`.

### IN-05: Pagination `_size` choices `[25, 50, 100]` are a magic list

**File:** `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/pagination.html:12`
**Issue:** Hard-coded in template; if the team wants to expose this in metadata or env later, all template edits cluster here.
**Fix:** Move to a context value (e.g. `pagination_size_options`) computed in `routes_table.py`. Low-priority cosmetic.

### IN-06: `verify_phase_05.sh` mixes `set -euo pipefail` with `|| echo "__CURL_FAIL__"` — pipeline-error escape hatch is fine, but `python -c` blocks lack `set -e`

**File:** `scripts/verify_phase_05.sh:170-173, 199-213, 217-218`
**Issue:** Bash safety review: `set -euo pipefail` is present (line 14). Quoted variables look right (`"$BASE_URL"`, `"$BODY"`, `"$PK"`, `"$HINT_TABLE"`). No `eval`. `curl -fsS … || echo "__CURL_FAIL__"` is the documented escape hatch and is consistent. One observation: lines 170-173 and 199-213 read JSON via inline `python -c`; if that pipeline produces an error the `|| echo` doesn't catch it because the error path emits an empty string from `python` (handled by the `if [ -z "$PK" ]` check that follows). The script handles all the failure modes I checked. The values that flow into `curl` URLs (`$PK`, `$HINT_TABLE`, `$ROW_PK`) come from the deployed datasette via JSON parsing — not from the user — so command-injection risk is low (and they're quoted into the URL string, so even adversarial values would not break out of the URL). Solid.
**Fix:** None required. Optional: add `IFS=$'\n\t'` after `set -euo pipefail` to harden word-splitting on filenames with spaces (none in scope, but defensive).

---

_Reviewed: 2026-04-25T11:35:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

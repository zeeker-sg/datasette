---
phase: 06-port-auxiliary-pages
reviewed: 2026-04-26T02:38:40Z
depth: standard
files_reviewed: 31
files_reviewed_list:
  - packages/zeeker-frontend/pyproject.toml
  - packages/zeeker-frontend/src/zeeker_frontend/changelog.py
  - packages/zeeker-frontend/src/zeeker_frontend/data/changelog.yaml
  - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py
  - packages/zeeker-frontend/src/zeeker_frontend/main.py
  - packages/zeeker-frontend/src/zeeker_frontend/routes_aux.py
  - packages/zeeker-frontend/src/zeeker_frontend/routes_search.py
  - packages/zeeker-frontend/src/zeeker_frontend/routes_sql.py
  - packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css
  - packages/zeeker-frontend/src/zeeker_frontend/static/robots.txt
  - packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/search_result.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/base.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/llms.txt
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/about.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/developers.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/how_to_use.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/search.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/sources.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/sql_db.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/sql_landing.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/pages/status.html
  - packages/zeeker-frontend/tests/fixtures/headlines_search_results.json
  - packages/zeeker-frontend/tests/fixtures/metadata_with_canned_queries.json
  - packages/zeeker-frontend/tests/fixtures/searchable_databases.json
  - packages/zeeker-frontend/tests/fixtures/sql_error_400.json
  - packages/zeeker-frontend/tests/test_changelog.py
  - packages/zeeker-frontend/tests/test_datasette_client_phase06.py
  - packages/zeeker-frontend/tests/test_routes_aux.py
  - packages/zeeker-frontend/tests/test_routes_search.py
  - packages/zeeker-frontend/tests/test_routes_sql.py
  - scripts/verify_phase_06.sh
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-04-26T02:38:40Z
**Depth:** standard
**Files Reviewed:** 31
**Status:** issues_found

## Summary

Phase 6 ports M1 auxiliary pages (`/about`, `/how-to-use`, `/sources`, `/status`, `/developers`, `/llms.txt`, `/robots.txt`) plus a new `/search` cross-database FTS UI and a `/sql` editor family into the FastAPI shell. The core threat-model surfaces are handled well: the SQL `_param_*` allowlist with `_PARAM_RE.fullmatch(":" + name)` correctly closes the form-key smuggling vector; reflected XSS in `/search` is prevented by Jinja autoescape; the `read body BEFORE raise_for_status()` pattern is correctly applied in `execute_sql` for friendly 400 errors; `asyncio.gather(return_exceptions=True)` plus `_safe_search_one` correctly isolate per-table failures in `/search`; and the `discover_searchable_tables` cache degrades to an empty dict on boot-time upstream errors with a friendly 503 in the UI.

No Critical issues were found. Three Warnings: (1) a malformed CSS comment block at the tail of `zeeker.css` produces orphan text outside any comment delimiters that may cause CSS parsers to drop the subsequent footer-link override rules; (2) `execute_sql` does not catch `ValueError`/`json.JSONDecodeError` so a non-JSON upstream response would propagate as an unhandled 500 to the user; (3) `/search` result links use Jinja's generic `urlencode` filter instead of `tilde_encode`, which can produce broken row links for primary keys containing `/`, `~`, or other non-`urlencode`-safe characters that Datasette expects tilde-encoded. Six Info-level items cover redundant filters, a dead query parameter, an empty CSS rule, and minor HTML/UX polish.

## Warnings

### WR-01: Malformed CSS comment leaves orphan text outside any comment block

**File:** `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css:2495-2502`
**Issue:** The "HARVESTED FROM M1 zeeker-base.css LINES 4097..4116 — Tail footer link override" comment ends at line 2498 with `======================================================= */`, but lines 2499–2500 contain free-floating text starting with `*`:

```css
/* =======================================================
   HARVESTED FROM M1 zeeker-base.css LINES 4097..4116
   Tail footer link override
   ======================================================= */
 *     idx column ("01", "02") gets breathing room from the container edge —
 *     especially visible on the database page table list. */

/* ----------------------------------------------------------------
 * FOOTER LINK OVERRIDE — must remain at TAIL of file to win cascade
```

These two lines are not inside a CSS comment — the `*/` on line 2498 closed the previous comment, and the `*/` on line 2500 is a stray comment-close. CSS parsers see `*` as a universal-selector token and try to parse `* idx column ("01", "02")...` as a selector. Standard CSS error-recovery skips until the next `;` or `}`, which means the parser may swallow the start of the immediately-following `FOOTER LINK OVERRIDE` comment and (depending on the implementation) the `footer a:link, footer a:visited, footer a:active { ... }` rule that follows. That rule is documented as load-bearing — it must remain at the tail of the file to beat Datasette's `footer a:link` rule via cascade order — so a parse skip here would silently regress footer link styling.

**Fix:** Delete the orphan lines (or wrap them in a fresh comment):

```css
/* =======================================================
   HARVESTED FROM M1 zeeker-base.css LINES 4097..4116
   Tail footer link override
   ======================================================= */

/* ----------------------------------------------------------------
 * FOOTER LINK OVERRIDE — must remain at TAIL of file to win cascade
 * against Datasette's /-/static/app.css `footer a:link` rule.
 * See .planning/notes/datasette-styling-limits.md WARN-05.
 * ---------------------------------------------------------------- */
```

### WR-02: execute_sql does not catch json-decode errors; non-JSON upstream → unhandled 500

**File:** `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py:213-220`
**Issue:** Inside `execute_sql`, after the 404 short-circuit, the body is parsed with `body = r.json()` *before* the 400 check (correct per Pitfall 1 / threat T-06-02-03). However, `r.json()` raises `json.JSONDecodeError` (a subclass of `ValueError`) when the upstream returns non-JSON — for example, a Caddy 502 HTML page or a Datasette HTML error page. `routes_sql.sql_db_post` only catches `httpx.HTTPError`:

```python
try:
    body, error = await execute_sql(client, db, sql, bound)
except httpx.HTTPError:
    raise HTTPException(503, "Data API unavailable")
```

A `ValueError` propagates past this except and surfaces to the user as a generic 500 from FastAPI's default error handler — leaking a stack trace in DEBUG, and producing a worse UX than the `_safe_search_one` partner (which already catches `(httpx.HTTPError, ValueError)`).

**Fix:** Either catch `ValueError` inside `execute_sql` and convert to a friendly error tuple, or widen the exception handler in `routes_sql.sql_db_post`. The cleanest fix is in the client (mirrors the `_safe_search_one` pattern):

```python
async def execute_sql(...) -> tuple[dict | None, str | None]:
    ...
    r = await client.get(f"/{db}.json", params=ds_params)
    if r.status_code == 404:
        return None, "Database not found"
    try:
        body = r.json()
    except ValueError:
        return None, "Upstream returned invalid JSON"
    if r.status_code == 400:
        return None, body.get("error") or "Query failed"
    r.raise_for_status()
    return body, body.get("error")
```

### WR-03: /search row links use generic urlencode, not tilde_encode — broken PKs with `/` or `~`

**File:** `packages/zeeker-frontend/src/zeeker_frontend/templates/_partials/search_result.html:27`
**Issue:** The `_partials/search_result.html` partial builds the row link with Jinja's generic `urlencode` filter:

```html
<a href="/{{ group.db }}/{{ group.table }}/{{ row._pk_str|urlencode }}">{{ row["__title__"] }}</a>
```

Datasette's row endpoint expects primary-key segments to be **tilde-encoded** (`tilde_encode`/`utils/__init__.py:1173-1186`), not URL-percent-encoded. The Phase 5 `urls.row_url` helper correctly composes a `tilde_encode(str(v))` per PK column — but `routes_search.search` flattens the PK into `row["_pk_str"] = ",".join(str(v) for v in primary_keys)` and the partial then `|urlencode`s the whole string. For PK values containing `/`, `~`, `+`, or whitespace, the resulting URL won't match Datasette's row router, producing a 404 from the link.

The fixture-driven tests don't exercise this because both fixture PKs are 32-char hex hashes (URL-safe). Production data with slugs, paths, or non-ASCII PKs will hit it.

**Fix:** Have the route build the full row href with `tilde_encode` and pass it on the row, or expose `tilde_encode` to the partial. Minimal patch — in `routes_search.py` after `_derive_pk_value`, attach a properly tilde-encoded path:

```python
from zeeker_frontend.urls import tilde_encode, row_url
...
for row in rows:
    pk_values = [row.get(k) for k in primary_keys] if primary_keys else []
    if pk_values and all(v is not None for v in pk_values):
        row["_row_href"] = row_url(db, t, [str(v) for v in pk_values])
    else:
        row["_row_href"] = None
    ...
```

Then in `_partials/search_result.html`:

```html
{% if row._row_href %}
  <a href="{{ row._row_href }}">{{ row["__title__"] }}</a>
{% else %}
  <a href="/{{ group.db }}/{{ group.table }}?_search={{ q|urlencode }}">{{ row["__title__"] }}</a>
{% endif %}
```

This routes through the existing tilde-encoder rather than relying on the partial to know the encoding rule.

## Info

### IN-01: Unused `_retry` query parameter in /search handler

**File:** `packages/zeeker-frontend/src/zeeker_frontend/routes_search.py:89`
**Issue:** The handler signature declares `_retry: int = 0` but the parameter is never read — only the failures-notice template builds a `?q=…&_retry=1` retry link. Accepting it on the handler is harmless (it doesn't change behaviour), but a reader looks for a code path that uses it and finds none. Dead parameter.

**Fix:** Either drop `_retry` from the signature (the link still works because FastAPI ignores unknown query params), or wire it to bypass the response cache (e.g., emit a different `Cache-Control` when `_retry=1`).

### IN-02: Failures-notice retry link uses bare `&` instead of `&amp;`

**File:** `packages/zeeker-frontend/src/zeeker_frontend/templates/pages/search.html:67`
**Issue:** `<a href="?q={{ q|urlencode }}&_retry=1">Retry →</a>` — strict HTML5 requires `&` in attribute values to be entity-escaped as `&amp;` (browsers do the right thing in practice, but HTML validators flag it).

**Fix:** `<a href="?q={{ q|urlencode }}&amp;_retry=1">Retry →</a>`.

### IN-03: Redundant `_zeeker` filter in templates after _collect_db_blocks already filtered

**File:** `packages/zeeker-frontend/src/zeeker_frontend/templates/pages/sources.html:67`, `packages/zeeker-frontend/src/zeeker_frontend/templates/pages/developers.html:148`
**Issue:** `_collect_db_blocks` in `routes_aux.py` already filters `_zeeker_*` (and any `hidden:true`) tables before populating `db.tables`. Both templates re-filter:

```html
{% for table in db.tables[:5] if not table.name.startswith('_zeeker') %}   {# sources.html #}
{% for table in db.tables if not table.name.startswith('_zeeker') %}        {# developers.html #}
```

In `sources.html` the filter follows a `[:5]` slice — if the (already-filtered) list ever changes shape so that the first 5 entries did include `_zeeker_*` rows, the user would see fewer than 5 tables. Today it's a no-op, but it's defensive code that obscures where the filter actually lives.

**Fix:** Drop the `if not table.name.startswith('_zeeker')` clause from both templates; the filter contract belongs to `_collect_db_blocks`. If you want defence in depth, keep the filter but document that it duplicates `_hidden(t)` in `routes_aux.py`.

### IN-04: `__title__` row key collides with a future Datasette column literally named `__title__`

**File:** `packages/zeeker-frontend/src/zeeker_frontend/routes_search.py:154-164`
**Issue:** The handler attaches a synthetic field on each row: `row["__title__"] = ...`. If Datasette ever returns a column literally named `__title__` (or a user CREATEs such a column), the handler would silently overwrite the upstream value. Probability is low (double-underscore is a Python convention, not SQL), but the `_pk_str` synthetic key already uses a single-underscore prefix that mirrors Datasette's `_*` reserved-key convention — `__title__` doesn't.

**Fix:** Rename the synthetic key to `_zfe_title` (or any prefix that's clearly frontend-internal) and update `_partials/search_result.html` to match.

### IN-05: Empty CSS rule `.page-search .search-hero`

**File:** `packages/zeeker-frontend/src/zeeker_frontend/static/css/zeeker.css:2159-2161`
**Issue:** The rule has only a `/* extends .guide-hero */` comment and zero declarations. Valid CSS but inert.

**Fix:** Either add the planned declarations or delete the rule and rely on the existing `.guide-hero` class on the same element.

### IN-06: On-200-with-error responses render both results AND error block in /sql template

**File:** `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py:220` and `packages/zeeker-frontend/src/zeeker_frontend/templates/pages/sql_db.html:46-66`
**Issue:** `execute_sql` returns `(body, body.get("error"))` even on 200. The handler passes both to the template. `sql_db.html` uses `{% if error %}` and `{% if results %}` independently, so a 200 response with a non-null `error` field would render both the `.sql-error` block AND the results table. Datasette rarely emits this shape (200 + error is documented as "rare" in the docstring), but the template doesn't reflect that contract — UX would show a confusing "query error" plus a populated table. No test fixture covers this case.

**Fix:** Either treat 200-with-error as an error-only state in the handler:

```python
body, error = await execute_sql(client, db, sql, bound)
if error:
    body = None
```

…or guard the results section in the template: `{% if results and not error %}`.

---

_Reviewed: 2026-04-26T02:38:40Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
phase: 04-port-home-database-pages
reviewed: 2026-04-22T00:00:00Z
depth: standard
reviewer: Claude (gsd-code-reviewer)
files_reviewed: 16
files_reviewed_list:
  - packages/zeeker-frontend/src/zeeker_frontend/main.py
  - packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py
  - packages/zeeker-frontend/src/zeeker_frontend/filters.py
  - packages/zeeker-frontend/src/zeeker_frontend/routes_home.py
  - packages/zeeker-frontend/src/zeeker_frontend/routes_database.py
  - packages/zeeker-frontend/src/zeeker_frontend/templates/base.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/index.html
  - packages/zeeker-frontend/src/zeeker_frontend/templates/database.html
  - packages/zeeker-frontend/pyproject.toml
  - packages/zeeker-frontend/tests/conftest.py
  - packages/zeeker-frontend/tests/test_home.py
  - packages/zeeker-frontend/tests/test_database.py
  - packages/zeeker-frontend/tests/test_client.py
  - packages/zeeker-frontend/tests/test_filters.py
  - packages/zeeker-frontend/tests/test_frontend.py
  - Caddyfile.prod
  - docker-compose.prod.yml
  - scripts/verify_phase_04.sh
findings:
  blocker: 0
  high: 1
  medium: 2
  low: 3
  info: 3
  total: 9
status: issues
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-22
**Depth:** standard
**Files Reviewed:** 16 (+ fixtures: databases.json, sglawwatch.json, metadata.json)
**Status:** issues (1 HIGH)

## Summary

Phase 4 ports two FastAPI/Jinja2 HTML routes (`GET /`, `GET /{db}`) from the M1 Datasette-plugin architecture. The architecture is sound: lifespan-scoped httpx client, Starlette's Jinja2Templates (autoescape on by default), TTL metadata cache, clean 503/404 error handling, and route registration order is correct. The test suite exercises the full stack with MockTransport and covers the key correctness properties.

One HIGH finding: the module-level metadata cache in `datasette_client.py` is a shared mutable dict with a time-of-check/time-of-use race under concurrent async requests — two coroutines can simultaneously bypass the expiry guard and both write to the cache, producing a benign double-write today but creating a reliability hazard when a third field is added. Two MEDIUM findings: (1) the `pluralize` filter's comma-form convention is inverted from the Django/Jinja2 standard (which would cause wrong output if the call sites are ever updated to match the standard), and (2) the `_zeeker_updates` table in the test fixture has `hidden: false`, which correctly exercises the prefix-based filter path — but no test explicitly asserts that a `_zeeker_*` table with `hidden: false` is excluded, leaving the prefix-filter branch untested. The BLOCKER-risk `javascript:` href injection in nav `menu_links` is mitigated by the fact that `metadata.json` is operator-controlled config, downgrading it to LOW.

---

## HIGH Issues

### H-01: Metadata cache TOCTOU race — double-write under concurrent async requests

**File:** `packages/zeeker-frontend/src/zeeker_frontend/datasette_client.py:44-55`
**Category:** Correctness / Concurrency

The TTL guard is a read-check-then-write sequence with no locking. In asyncio, two coroutines that both find `payload is None` (or find `now >= expires_at`) before either has written the new value will both call `client.get("/-/metadata.json")` and both write to the cache dict. Under Python's GIL this is a benign double-write today (last writer wins, values are identical). However:

1. If a future change adds a second cache field (e.g. per-db metadata), the interleaved writes could produce a partially-updated dict.
2. The current code structure trains readers to believe the cache is always consistent after the first call, which is not guaranteed.

The fix is a standard asyncio lock or a "check, set sentinel, then fill" pattern.

**Remediation:**

```python
import asyncio

_METADATA_LOCK = asyncio.Lock()

async def fetch_site_metadata(client: httpx.AsyncClient) -> dict:
    """GET /-/metadata.json with 60s TTL cache; empty dict on transport error."""
    now = time.monotonic()
    if _METADATA_CACHE["payload"] is not None and now < _METADATA_CACHE["expires_at"]:
        return _METADATA_CACHE["payload"]
    async with _METADATA_LOCK:
        # Re-check inside the lock (double-checked locking for async).
        now = time.monotonic()
        if _METADATA_CACHE["payload"] is not None and now < _METADATA_CACHE["expires_at"]:
            return _METADATA_CACHE["payload"]
        try:
            r = await client.get("/-/metadata.json")
            r.raise_for_status()
            payload = r.json()
        except httpx.HTTPError:
            return {}
        _METADATA_CACHE["payload"] = payload
        _METADATA_CACHE["expires_at"] = now + _METADATA_TTL_SECONDS
        return payload
```

Also update `reset_metadata_cache()` to preserve compatibility with the test helper.

---

## MEDIUM Issues

### M-01: `pluralize` comma-form convention is inverted from standard

**File:** `packages/zeeker-frontend/src/zeeker_frontend/filters.py:41-49`
**Category:** Correctness / Quality

The comma-form `arg` for `pluralize` is documented and tested as `"plural_form,singular_form"` (e.g. `"ies,y"` → singular is "y", plural is "ies"). The Django/Jinja2 standard convention (and the M1 M1 port's assumed convention) is the opposite: `"singular_suffix,plural_suffix"`. The variable names at line 48 reinforce the confusion: `plural_suffix, singular_suffix = str(arg).split(",", 1)` — the first element is named `plural_suffix` but receives the first token (which *is* used as the plural), so the implementation is internally consistent. The tests confirm the current behaviour.

The risk: if any future call site follows the standard `"singular,plural"` convention, the filter silently produces inverted output. M1 templates in this phase do not use the comma-form directly (the phase-4 templates use `plural()` not `pluralize()` with commas), so there is no active breakage — but the non-standard API is a maintainability hazard.

**Remediation:** Either flip the convention to the standard `"singular_suffix,plural_suffix"` (and update tests), or rename the variables to remove the misleading labels:

```python
# Option A: flip to standard (singular,plural)
plural_form, singular_form = str(arg).split(",", 1)
return singular_form.strip() if n == 1 else plural_form.strip()
# → test: pluralize(1, "y,ies") == "y"; pluralize(2, "y,ies") == "ies"

# Option B: keep current behaviour, fix names only (no convention change)
first_form, second_form = str(arg).split(",", 1)
# first_form = used for plural; second_form = used for singular
return second_form.strip() if n == 1 else first_form.strip()
```

Option A (standard convention) is preferred to avoid future confusion.

---

### M-02: Prefix-filter branch for `_zeeker_*` tables with `hidden: false` is not directly tested

**File:** `packages/zeeker-frontend/tests/test_database.py:76-84`
**Category:** Test quality / Correctness

`test_database_filters_hidden_zeeker_tables` asserts `"_zeeker" not in r.text`. The fixture `sglawwatch.json` contains `_zeeker_updates` with `"hidden": false` (line 74 of the fixture). The route handler at `routes_database.py:35` filters by `not t.get("hidden") and not t.get("name", "").startswith("_zeeker")` — the AND means a table that is `hidden: false` but prefixed `_zeeker_` is excluded by the prefix clause.

The test assertion (`"_zeeker" not in r.text`) *does* cover this case implicitly, because the fixture includes `_zeeker_updates` with `hidden: false`. However, if the prefix filter is accidentally removed (leaving only the `hidden` flag check), the test would catch the leak — so the coverage is correct. The gap is that the test comment says "The captured fixture includes `_zeeker_*` tables with hidden=true" (line 79), which is inaccurate: `_zeeker_updates` has `hidden: false`. A developer reading only the test comment would believe the prefix filter is redundant.

**Remediation:** Update the test docstring to accurately describe the fixture:

```python
async def test_database_filters_hidden_zeeker_tables(client_with_mocked_datasette):
    """The fixture includes _zeeker_* tables, some with hidden=True (via Datasette
    metadata.json) and at least one (_zeeker_updates) with hidden=False.
    The prefix-AND-flag filter in routes_database must exclude ALL of them."""
    r = await client_with_mocked_datasette.get("/sglawwatch")
    assert "_zeeker" not in r.text, (
        "Hidden _zeeker_* tables leaked into the rendered page"
    )
```

Consider also adding a dedicated test that constructs a minimal payload with a `_zeeker_*` table that has `hidden: false` and asserts it is filtered.

---

## LOW Issues

### L-01: `menu_links[*].href` rendered unvalidated into HTML `href` attributes

**File:** `packages/zeeker-frontend/src/zeeker_frontend/templates/base.html:21`
**Category:** Security / XSS

`{{ link.href }}` at line 21 is rendered inside `href="{{ link.href }}"`. Jinja2's autoescape encodes `"` → `&quot;` and `<` → `&lt;`, which prevents attribute-break XSS. However, it does not strip `javascript:` URI schemes, so a `metadata.json` entry of `{"href": "javascript:alert(1)", "label": "X"}` would produce a clickable XSS vector.

**Mitigating context:** `metadata.json` is operator-controlled config committed to the repository — not user input. The risk only materialises if the file is edited maliciously or the `/-/metadata.json` endpoint is writable. This is therefore LOW rather than HIGH.

**Remediation (optional but hardening):** Add a Jinja2 filter that enforces an allowlist of schemes:

```python
# filters.py
import urllib.parse

def safe_href(value: str) -> str:
    """Allow only http/https/relative hrefs — strips javascript: et al."""
    if isinstance(value, str):
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in ("", "http", "https"):
            return "#"
    return value

# main.py: templates.env.filters["safe_href"] = zfilters.safe_href
# base.html: <a href="{{ link.href | safe_href }}">
```

---

### L-02: `|safe` applied to `s()` return values establishes a dangerous pattern

**File:** `packages/zeeker-frontend/src/zeeker_frontend/templates/index.html:17-19, 83-84, 135-138, 163-169`
**Category:** Security / Code Quality

`{{ s('home_hero_primary', 'Public data,')|safe }}` and similar calls mark the output of `s()` as HTML-safe, bypassing autoescape. Today `s()` is a stub that returns its `default` argument — a string literal written by the developer. There is no injection risk.

The hazard is future-state: if `s()` is later backed by a YAML file, a database, or any external source, every `|safe` call site becomes an unescaped injection point. The pattern was inherited from M1's string_manager where the `s()` contract was also developer-controlled, so this is a known trade-off.

**Remediation:** Document the constraint in `filters.py` at the `s()` function definition:

```python
def s(key: str, default: str = "") -> str:
    """String lookup — stub; returns default (no strings.yaml in frontend).

    IMPORTANT: Templates call {{ s(...) | safe }} — if this stub is ever
    replaced with an external data source, all |safe call sites must be
    audited for injection before shipping.
    """
    return default
```

No code change is required now; the comment is the fix.

---

### L-03: `verify_phase_04.sh` uses `set -euo pipefail` but suppresses errors in assertion blocks inconsistently

**File:** `scripts/verify_phase_04.sh:19, 58-82`
**Category:** Code Quality / Test reliability

The script sets `set -euo pipefail` at line 19. Within the assertion block (lines 58-82) several checks use `|| fail "..."` to prevent early exit, but the overall FAILED aggregation is correct. However, `BODY=$(curl -fsS ... || echo "__CURL_FAIL__")` at line 52: if curl fails with a non-zero exit, the subshell substitution succeeds (prints `__CURL_FAIL__`), which is the intended guard. This is fine.

A subtler issue: the `|| true` comment in the header (line 16) says assertions are "OR'd with `|| true` where appropriate" but only `fail` blocks suppress the exit — `ok` blocks that call `grep -q` don't use `|| true`. The pattern `echo "$BODY" | grep -q '...' && ok "..." || fail "..."` is correct because `grep -q` returns 1 on no-match, which is caught by `|| fail`, not `|| true`. This is correct but the comment is misleading.

**Remediation:** Update the header comment to accurately describe the `&& ok || fail` idiom. No functional change needed.

---

## INFO Items

### I-01: `test_home_renders_card_per_database` would pass even if hidden databases were leaked

**File:** `packages/zeeker-frontend/tests/test_home.py:87-93`
**Category:** Test quality

The test asserts `card_count == len(databases_fixture)`. The `databases_fixture` contains 3 databases, none with `hidden: true`. The route handler filters `visible_dbs = [d for d in databases if not d.get("hidden")]`. Because no database in the fixture is hidden, this test would pass even if the hidden-filter were removed. If future fixtures include a hidden database, the test would correctly fail.

**Observation:** Acceptable for now given the fixture is synthetic. A future improvement would add a `"hidden_db"` entry with `hidden: true` to the fixture to ensure the filter is load-bearing.

---

### I-02: `conftest.py` `mock_datasette` fixture returns an unclosed `AsyncClient`

**File:** `packages/zeeker-frontend/tests/conftest.py:60-64`
**Category:** Test quality / Resource leak

The `mock_datasette` fixture returns an `httpx.AsyncClient` directly (not as an async context manager). Tests in `test_client.py` use it as `async with mock_datasette as client:`, which works because `httpx.AsyncClient` implements `__aenter__`/`__aexit__`. However, the fixture itself does not explicitly close the client if a test bypasses the `async with`. This is a minor resource leak in the test process only and has no production impact.

**Observation:** Low-priority; the current usage pattern is safe. Note for completeness.

---

### I-03: `pyproject.toml` version field is stale (`0.1.0`) despite app running at `version="0.4.0"`

**File:** `packages/zeeker-frontend/pyproject.toml:3`
**Category:** Config hygiene

`pyproject.toml` line 3: `version = "0.1.0"`. `main.py` line 57: `version="0.4.0"`. These are independent (pyproject is the package version; FastAPI's `version` is the OpenAPI spec version), but the divergence is confusing and suggests the pyproject version was never updated.

**Remediation:** Update `pyproject.toml` to `version = "0.4.0"` to match the phase milestone, or document that the two version fields serve different purposes.

---

## Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| H-01 | HIGH | `datasette_client.py:44-55` | Metadata cache TOCTOU race under concurrent async requests |
| M-01 | MEDIUM | `filters.py:41-49` | `pluralize` comma-form convention inverted from standard |
| M-02 | MEDIUM | `tests/test_database.py:79` | Inaccurate test comment obscures _zeeker_ prefix-filter branch coverage |
| L-01 | LOW | `templates/base.html:21` | `menu_links` href rendered without scheme-allowlist check |
| L-02 | LOW | `templates/index.html:17-19, 83-84, 135-138, 163-169` | `\|safe` on `s()` output creates future injection risk |
| L-03 | LOW | `scripts/verify_phase_04.sh:16` | Misleading header comment about `|| true` usage |
| I-01 | INFO | `tests/test_home.py:87-93` | Hidden-db filter not load-bearing in current fixture |
| I-02 | INFO | `tests/conftest.py:60-64` | `mock_datasette` fixture returns unclosed async client |
| I-03 | INFO | `pyproject.toml:3` | Package version `0.1.0` diverges from FastAPI version `0.4.0` |

---

_Reviewed: 2026-04-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

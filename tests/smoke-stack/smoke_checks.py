#!/usr/bin/env python3
"""
smoke_checks.py — production-shaped end-to-end smoke against the disposable
smoke stack. Base URL via SMOKE_BASE_URL (default http://127.0.0.1:8891).

Layers exercised through the real caddy entry:
  caddy -> datasette (suffix matcher)      /-/versions.json
  caddy -> frontend (catch-all)            /frontend-test, /, /{db}, /status
  frontend -> datasette (internal client)  any 200 /{db} page proves the
                                           cross-container hop + boot probes
  data API                                 table/row JSON, CSV, staff routes
  search-all + ?_search=                   datasette-search-all surface
  content lockdown                         strip_columns, cache_headers,
                                           edge SQL/FTS responses
All fixtures are synthetic ("SMOKETEST" markers). Exit 0 = all checks pass.
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8891").rstrip("/")
TOKEN = os.environ.get("SMOKE_OWNER_TOKEN", "smoke-owner-token-local-only")
SECRET_PREFIX = "SMOKETEST"  # marker prefix used inside protected fixture text

FAILS: list[str] = []


def fetch(path: str, headers=None):
    """GET a stack URL. Returns (status, HTTPMessage-headers, body-bytes).

    headers stays the raw case-insensitive HTTPMessage (dict() would break
    case-insensitive lookups of e.g. Cache-Control)."""
    req = urllib.request.Request(BASE + path, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


def text(resp):
    return resp[2].decode("utf-8", "replace")


def jbody(resp):
    return json.loads(text(resp))


def expect(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILS.append(name)


def run_checks() -> None:
    # 1 — caddy -> datasette via the *.json / /-* suffix matcher (docker DNS)
    status, headers, raw = fetch("/-/versions.json")
    expect("caddy routes /-/* to datasette (200)", status == 200, f"got {status}")
    version = jbody((status, headers, raw))["datasette"]["version"] if status == 200 else None
    expect("datasette reports its version", bool(version), "no datasette.version")

    # 2 — caddy catch-all -> frontend
    status, headers, raw = fetch("/frontend-test")
    expect("caddy routes catch-all to frontend", status == 200, f"got {status}")
    status, headers, raw = fetch("/")
    expect(
        "frontend homepage renders HTML",
        status == 200
        and text((status, headers, raw)).lstrip().lower().startswith(("<!doctype html", "<html")),
        f"got {status}",
    )

    # 3 — frontend -> datasette over the internal bridge
    status, headers, raw = fetch("/news")
    expect("frontend /{db} page (internal datasette client)", status == 200, f"got {status}")
    expect("frontend /{db} page lists fixture tables", "mlaw_news" in text((status, headers, raw)))

    # 4 — data API: table/row JSON, CSV contract, staff endpoints
    status, headers, raw = fetch("/news/mlaw_news.json")
    expect("table .json 200", status == 200, f"got {status}")
    data = jbody((status, headers, raw))
    expect("table .json shape has rows+columns", "rows" in data and "columns" in data)
    expect("protected column stripped (columns)", "content_text" not in data["columns"])
    expect("protected values absent (rows)", SECRET_PREFIX not in json.dumps(data), "LEAK")

    status, headers, raw = fetch("/news/mlaw_news/1.json")
    row = jbody((status, headers, raw))
    expect("row .json 200 + stripped", status == 200 and "content_text" not in row["columns"], f"got {status}")

    status, headers, raw = fetch("/news/mlaw_news.csv")
    expect(
        "CSV blocked on protected table (403 + .json hint)",
        status == 403 and ".json" in text((status, headers, raw)),
        f"got {status}",
    )
    status, headers, raw = fetch("/laws/headlines.csv")
    expect("CSV allowed on clean table (200)", status == 200, f"got {status}")

    status, headers, raw = fetch("/-/metadata.json")
    expect("staff metadata reachable", status == 200, f"got {status}")

    # 5 — datasette-search-all: page lists searchable tables; ?_search= works
    status, headers, raw = fetch("/-/search?q=Smoke")
    expect("cross-DB search page lists tables", status == 200 and "mlaw_news" in text((status, headers, raw)), f"got {status}")
    status, headers, raw = fetch("/news/mlaw_news.json?_search=Smoke&_shape=objects")
    data = jbody((status, headers, raw))
    expect("?_search= returns matches", status == 200 and bool(data.get("rows")), f"got {status}")
    expect("?_search= rows stripped", "content_text" not in data["columns"])
    expect("?_search= carries no protected values", SECRET_PREFIX not in json.dumps(data["rows"]), "LEAK")

    # 6 — lockdown + headers at the edge
    status, headers, raw = fetch("/news.json?sql=select+content_text+from+mlaw_news")
    expect("arbitrary SQL denied (403)", status == 403, f"got {status}")
    status, headers, raw = fetch("/news/mlaw_news_fts.json")
    expect("FTS shadow blocked (caddy 403)", status == 403, f"got {status}")
    status, headers, raw = fetch("/news/mlaw_news.json")
    expect(
        "cache_headers contract via caddy",
        headers.get("cache-control") == "public, max-age=300, s-maxage=3600",
        f"got {headers.get('cache-control')!r}",
    )
    status, headers, raw = fetch("/-/versions.json")
    expect("staff route not cached", "no-store" in headers.get("cache-control", ""), f"got {headers.get('cache-control')!r}")

    # 7 — owner bypass round-trip (same token handed to the container)
    status, headers, raw = fetch(
        "/news/mlaw_news.json?_shape=objects", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    if status == 200:
        rows = jbody((status, headers, raw)).get("rows", [])
        expect("owner token bypasses strip (full JSON)", any(SECRET_PREFIX in json.dumps(r) for r in rows))
    else:
        expect("owner token request reaches datasette", False, f"got {status}")

    # 8 — status page (frontend static content)
    status, headers, raw = fetch("/status")
    expect("frontend /status renders", status == 200, f"got {status}")


if __name__ == "__main__":
    run_checks()
    print()
    if FAILS:
        print(f"SMOKE FAILED: {len(FAILS)} failing check(s): {', '.join(FAILS)}")
        sys.exit(1)
    print("SMOKE PASSED: all checks green")
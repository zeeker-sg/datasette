# plugins/block_db_csv.py
"""
Database-level CSV guard: returns a clean 404 for `/{database}.csv`
requests instead of Datasette's 500.

Why: Datasette 0.65.2 (still in 0.65.3) routes `/{db}.csv` to
ViewBase.as_csv() (datasette/views/base.py:217), which reads
`data["columns"]` — but DatabaseView.data() returns the database-index
context (tables/views catalog) with no top-level "columns" key, so every
database-level CSV export raises KeyError and 500s. Upstream main has
since removed database-level CSV entirely (DatabaseView.get accepts only
html/json formats); this plugin brings that behaviour forward.

This surface is dead in the Zeeker deployment by design:
- The frontend owns all HTML/database pages and deliberately renders no
  /{db}.csv links (templates/database.html: "No /{db}.csv — database-level
  CSV requires a SQL query (removed).").
- Database-level CSV in Datasette is built on an ad-hoc `?sql=` SELECT,
  which this instance denies (default_allow_sql off + strip_columns 403s
  any ?sql=).

So the correct product behaviour is a 404 ("not available"), not a 500.
Table-level CSV (/{db}/{table}.csv) is unaffected and continues to work
(protected tables 403 via strip_columns).

The guard lives in the ASGI wrapper layer (same pattern as
strip_columns.py / cache_headers.py) so it survives Datasette version
bumps without touching vendored code.
"""

import functools

from datasette import hookimpl

# Body for the 404 we return instead of the 500.
_NOT_FOUND = b"Not found: database-level CSV export is not available. Use table URLs: /{database}/{table}.csv\n"


@hookimpl
def asgi_wrapper(datasette):
    def wrap_with_db_csv_guard(app):
        @functools.wraps(app)
        async def block_db_csv(scope, receive, send):
            if scope["type"] != "http":
                await app(scope, receive, send)
                return

            path = scope.get("path", "")

            # Match exactly "/<database>.csv": ends with .csv, is a single
            # path segment (the leading "/" only), and the stem is non-empty
            # (a lone "/.csv" is not a database route).
            if (
                scope.get("method", "GET") == "GET"
                and path.endswith(".csv")
                and path.count("/") == 1
                and len(path) > 5
            ):
                headers = [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(_NOT_FOUND)).encode()),
                ]
                await send(
                    {
                        "type": "http.response.start",
                        "status": 404,
                        "headers": headers,
                    }
                )
                await send({"type": "http.response.body", "body": _NOT_FOUND})
                return

            await app(scope, receive, send)

        return block_db_csv

    return wrap_with_db_csv_guard
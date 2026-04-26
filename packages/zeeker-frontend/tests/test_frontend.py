"""Phase 2 smoke tests for the zeeker-frontend placeholder.

The Phase-2 `test_unknown_path_returns_404` guard was retired in Phase 4:
`/{db}` is now an intentional catch-all (see routes_database). The healthcheck
and the sqlite3 fence still apply.
"""
from fastapi.testclient import TestClient


def test_frontend_test_returns_ok(client: TestClient) -> None:
    """GET /frontend-test returns the documented 200 + JSON body."""
    response = client.get("/frontend-test")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "zeeker-frontend"}


def test_module_does_not_top_level_import_sqlite3() -> None:
    """Package fence test — DEC-5 / REQ-frontend-data-via-http.

    zeeker_frontend.main MUST NOT import sqlite3 at module-load time. sqlite3
    is in stdlib so `import sqlite3` elsewhere would still succeed; this test
    just guards against the frontend module itself picking up SQLite habits.
    """
    # sqlite3 may already be imported by something else in the test process
    # (e.g. pytest internals). The useful check is: after freshly reimporting
    # zeeker_frontend.main, its own source doesn't reference sqlite3.
    import inspect

    import zeeker_frontend.main as m

    src = inspect.getsource(m)
    assert "sqlite3" not in src, (
        "zeeker_frontend.main references sqlite3 — "
        "violates DEC-5 (frontend reads data only via HTTP to datasette)."
    )

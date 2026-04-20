"""Phase 2 smoke tests for the zeeker-frontend placeholder."""
import sys

import pytest
from fastapi.testclient import TestClient


def test_frontend_test_returns_ok(client: TestClient) -> None:
    """GET /frontend-test returns the documented 200 + JSON body."""
    response = client.get("/frontend-test")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "zeeker-frontend"}


def test_unknown_path_returns_404(client: TestClient) -> None:
    """Phase 2 frontend has only one route; everything else is 404.

    This guards against someone accidentally adding a catch-all handler
    that would change Phase 3's forward-compat assumptions.
    """
    response = client.get("/some-other-path")
    assert response.status_code == 404


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

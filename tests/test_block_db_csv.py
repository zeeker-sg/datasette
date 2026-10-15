"""
Tests for the block_db_csv plugin (database-level CSV guard).

Runs a real Datasette instance over a temp SQLite database with the
plugin registered against datasette's plugin manager, and verifies:

- /{db}.csv → 404 with the helpful body (Datasette 0.65.2/0.65.3 would
  500 here with KeyError: 'columns' — views/base.py:217 as_csv).
- /{db}.json, table-level .csv/.json and ?_format=csv are untouched.
- Only exact "/<db>.csv" single-segment paths are intercepted.
"""

import sqlite3

import pytest
from datasette.app import Datasette
from datasette.plugins import pm

import plugins.block_db_csv as block_db_csv_module

PLUGIN_NAME = "block-db-csv-under-test"

CSV_404_BODY = block_db_csv_module._NOT_FOUND.decode()


@pytest.fixture(scope="module", autouse=True)
def register_plugin():
    pm.register(block_db_csv_module, name=PLUGIN_NAME)
    yield
    pm.unregister(name=PLUGIN_NAME)


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("block-db-csv") / "testdb.db"
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE clean (
            id INTEGER PRIMARY KEY,
            name TEXT
        );
        INSERT INTO clean VALUES (1, 'alpha'), (2, 'beta');
        """
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def ds(db_path):
    return Datasette([str(db_path)])


@pytest.mark.asyncio
async def test_db_csv_returns_404_not_500(ds):
    """The actual production bug: /{db}.csv must be a clean 404, not 500."""
    response = await ds.client.get("/testdb.csv")
    assert response.status_code == 404
    assert "not available" in response.text
    assert "table" in response.text


@pytest.mark.asyncio
async def test_db_csv_404_body_mentions_table_route(ds):
    """The 404 should point humans at the working table-level route."""
    response = await ds.client.get("/testdb.csv")
    assert "/{database}/{table}.csv" in response.text


@pytest.mark.asyncio
async def test_db_json_unaffected(ds):
    response = await ds.client.get("/testdb.json")
    assert response.status_code == 200
    assert response.json()["database"] == "testdb"


@pytest.mark.asyncio
async def test_table_csv_unaffected(ds):
    response = await ds.client.get("/testdb/clean.csv")
    assert response.status_code == 200
    assert "alpha" in response.text


@pytest.mark.asyncio
async def test_table_json_unaffected(ds):
    response = await ds.client.get("/testdb/clean.json?_shape=objects")
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert [r["name"] for r in rows] == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_format_csv_query_param_passes_through(ds):
    """/{db}?_format=csv is not the broken route — do not intercept it."""
    response = await ds.client.get("/testdb?_format=csv")
    assert response.status_code != 404 or "not available" not in response.text


@pytest.mark.asyncio
async def test_multi_segment_csv_paths_not_intercepted(ds):
    """Only exact single-segment /<db>.csv is guarded; deeper paths pass through."""
    # A table path ending in .csv but under the database namespace is NOT
    # the broken route (here: a genuinely missing table → Datasette 404s).
    response = await ds.client.get("/testdb/missing.csv")
    assert response.status_code == 404
    assert "not available" not in response.text


@pytest.mark.asyncio
async def test_root_dot_csv_not_intercepted(ds):
    """'/.csv' (empty database stem) must not be treated as a database route."""
    response = await ds.client.get("/.csv")
    # Datasette never routes this to DatabaseView — whatever it returns
    # (404/405), it must not be our guard's body.
    assert "not available" not in response.text


@pytest.mark.asyncio
async def test_non_get_methods_pass_through(ds):
    """The guard only intercepts GET — other methods reach the normal stack."""
    response = await ds.client.post("/testdb.csv")
    # POST on a GET-only route → Datasette's method-not-allowed (405), or
    # at minimum NOT our custom 404 body.
    assert "not available" not in response.text
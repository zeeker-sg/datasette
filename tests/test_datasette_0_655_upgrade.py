"""
Representative-path tests for the Datasette 0.65.5 dependency upgrade.

The upgrade commit pins datasette==0.65.5 (from 0.65.2) in pyproject.toml,
requirements.txt and uv.lock. This module exercises the deployment's real
request surface on the upgraded version: explicit plugin startup (the boot
path uvicorn/prod relies on), staff endpoints, the catalogue, table/row JSON,
CSV export behaviour, the cache_headers header contract, and cross-database
search via datasette-search-all — with the strip_columns content-protection
wrapper active throughout so no protected full text can leak on any path.

Runs against the installed datasette (uv-managed), mirroring the prod image
build (uv sync --frozen) and CI (uv sync --locked + uv run pytest).
"""

import json
import sqlite3

import pytest
from datasette.app import Datasette
from datasette.plugins import pm

import plugins.cache_headers as cache_headers_module
import plugins.strip_columns as strip_columns_module
from datasette import __version__ as datasette_version

PLUGIN_PREFIX = "upgrade-under-test"

METADATA = {
    "title": "upgrade-smoke",
    "allow_sql": {"id": "owner"},
    "plugins": {
        "strip-columns": {
            "default_deny_names": ["content_text"],
            "tables": {
                "news": {"mlaw_news": ["content_text"]},
            },
        }
    },
}

SETTINGS = {"default_allow_sql": False}


def _make_db(path, script):
    conn = sqlite3.connect(str(path))
    conn.executescript(script)
    conn.commit()
    conn.close()
    return path


@pytest.fixture(scope="module")
def db_news(tmp_path_factory):
    path = tmp_path_factory.mktemp("upgrade") / "news.db"
    return _make_db(
        path,
        """
        CREATE TABLE mlaw_news (
            id INTEGER PRIMARY KEY,
            title TEXT,
            summary TEXT,
            content_text TEXT
        );
        INSERT INTO mlaw_news VALUES
            (1, 'Mlaw one', 'Summary one', 'SECRET-BODY-ONE'),
            (2, 'Mlaw two', 'Summary two', 'SECRET-BODY-TWO');
        CREATE VIRTUAL TABLE mlaw_news_fts USING fts5(
            title, content_text, content=[mlaw_news]
        );
        INSERT INTO mlaw_news_fts(rowid, title, content_text)
            SELECT id, title, content_text FROM mlaw_news;
        """,
    )


@pytest.fixture(scope="module")
def db_laws(tmp_path_factory):
    path = tmp_path_factory.mktemp("upgrade") / "laws.db"
    return _make_db(
        path,
        """
        CREATE TABLE headlines (
            id INTEGER PRIMARY KEY,
            title TEXT,
            date TEXT
        );
        INSERT INTO headlines VALUES (1, 'Law headline', '2026-10-12');
        CREATE VIRTUAL TABLE headlines_fts USING fts5(title, content=[headlines]);
        INSERT INTO headlines_fts(rowid, title)
            SELECT id, title FROM headlines;
        """,
    )


@pytest.fixture(scope="module", autouse=True)
def register_plugins():
    pm.register(cache_headers_module, name=f"{PLUGIN_PREFIX}-cache-headers")
    pm.register(strip_columns_module, name=f"{PLUGIN_PREFIX}-strip-columns")
    yield
    pm.unregister(name=f"{PLUGIN_PREFIX}-cache-headers")
    pm.unregister(name=f"{PLUGIN_PREFIX}-strip-columns")


@pytest.fixture(scope="module")
def ds_factory(db_news, db_laws):
    def make():
        return Datasette(
            [str(db_news), str(db_laws)],
            metadata=dict(METADATA),
            settings=dict(SETTINGS),
        )

    return make


@pytest.fixture
def ds(ds_factory):
    return ds_factory()


# ------------------------------------------------------------------ bootstrap


def test_datasette_resolved_to_0_6_5_5():
    """The pinned dependency is the upgraded one — catches a stale venv/lock
    silently serving the old version to every other test in this module."""
    assert [int(p) for p in datasette_version.split(".")[:3]] == [0, 65, 5]


@pytest.mark.asyncio
async def test_explicit_invoke_startup_completes(ds):
    """invoke_startup must run every plugin hook (both custom plugins register
    routes/hooks through the plugin manager) cleanly on the new version —
    prod boots hit this exact path."""
    await ds.invoke_startup()


# ------------------------------------------------------------ staff endpoints


@pytest.mark.asyncio
async def test_versions_endpoint_reports_upgraded_datasette(ds):
    response = await ds.client.get("/-/versions.json")
    assert response.status_code == 200
    assert response.json()["datasette"]["version"] == "0.65.5"


@pytest.mark.asyncio
async def test_metadata_and_database_catalogue(ds):
    response = await ds.client.get("/-/metadata.json")
    assert response.status_code == 200
    body = response.json()
    assert body["allow_sql"] == {"id": "owner"}
    assert "strip-columns" in body["plugins"]

    response = await ds.client.get("/-/databases.json")
    assert response.status_code == 200
    names = {entry["name"] for entry in response.json()}
    assert names == {"news", "laws"}


# ------------------------------------------------------- table / row / shapes


@pytest.mark.asyncio
async def test_table_json_strips_protected_columns(ds):
    response = await ds.client.get("/news/mlaw_news.json")
    assert response.status_code == 200
    assert "SECRET" not in response.text
    data = response.json()
    assert "content_text" not in data["columns"]
    assert "summary" in data["columns"]
    for row in data["rows"]:
        assert len(row) == len(data["columns"])


@pytest.mark.asyncio
async def test_row_json_strips_protected_columns(ds):
    response = await ds.client.get("/news/mlaw_news/1.json")
    assert response.status_code == 200
    assert "SECRET" not in response.text
    assert "content_text" not in response.json()["columns"]


@pytest.mark.asyncio
async def test_csv_blocked_on_protected_table(ds):
    response = await ds.client.get("/news/mlaw_news.csv")
    assert response.status_code == 403
    assert "SECRET" not in response.text
    assert ".json" in response.text


@pytest.mark.asyncio
async def test_csv_ok_on_clean_table(ds):
    response = await ds.client.get("/laws/headlines.csv")
    assert response.status_code == 200
    assert response.text.replace("\r\n", "\n") == "id,title,date\n1,Law headline,2026-10-12\n"


# ------------------------------------------------------ cross-database search


@pytest.mark.asyncio
async def test_search_all_lists_searchable_tables(ds):
    """datasette-search-all must keep working on 0.65.x: its FTS detection is
    exactly what the 0.65.4 security backports touched (parameterized
    detection SQL, literal wildcard handling). With content-linked FTS
    (sqlite-utils-style), the /-/search page must list the searchable tables
    of both databases."""
    response = await ds.client.get("/-/search?q=Mlaw")
    assert response.status_code == 200
    assert "mlaw_news" in response.text
    assert "headlines" in response.text


@pytest.mark.asyncio
async def test_search_json_endpoint_returns_matches_without_full_text(ds):
    """The search page's results flow through the table's ?_search= JSON
    endpoint (that is what its JS fetches). Results must come back on the
    upgraded stack — with the protected column stripped from rows."""
    response = await ds.client.get(
        "/news/mlaw_news.json?_search=Mlaw&_shape=objects"
    )
    assert response.status_code == 200
    assert "SECRET" not in response.text
    data = response.json()
    titles = [row["title"] for row in data["rows"]]
    assert "Mlaw one" in titles
    for row in data["rows"]:
        assert "content_text" not in row


@pytest.mark.asyncio
async def test_search_endpoints_never_leak_protected_full_text(ds):
    """Search surfaces must never return protected full text.

    Response echoes of the caller's own query (Datasette repeats the search
    term in <title> and in human_description_en / the query.sql echo) are the
    user's input, not data — those fields are removed before the check, and
    the assertion below is about the actual payload: rows, columns, facets
    and any other served values.
    """
    echo_keys = {"human_description_en", "query"}

    async def served_clean(path, *echo_fields):
        response = await ds.client.get(path)
        assert response.status_code == 200, path
        data = json.loads(response.text)
        for field in (echo_fields or echo_keys):
            data.pop(field, None)
        assert "SECRET" not in json.dumps(data), path

    await served_clean("/news/mlaw_news.json?_search=SECRET-BODY-ONE")
    await served_clean("/laws/headlines.json?_search=Law+headline")

    # The HTML search page is pure template + the caller's query interpolated
    # into title, form field and per-table search links — it carries no rows.
    # The airtight structural check: the page for q=SECRET must be byte-
    # identical to the page for an inert marker query with the marker
    # re-colored to the secret. Any served DATA containing the protected
    # text would make the secret-page differ from the recolored marker-page.
    response = await ds.client.get("/-/search?q=SECRET-BODY-ONE")
    assert response.status_code == 200
    marker = await ds.client.get("/-/search?q=MARKER-QUERY-TEXT")
    assert marker.status_code == 200
    recolored = marker.text.replace("MARKER-QUERY-TEXT", "SECRET-BODY-ONE")
    assert recolored == response.text


# ------------------------------------------------------ caching contract


@pytest.mark.asyncio
async def test_catalogue_page_cache_contract(ds):
    """cache_headers must still take over Cache-Control from the app on the
    upgraded stack (prod contract: public, browser 5 min, CDN 1 hour)."""
    response = await ds.client.get("/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=300, s-maxage=3600"


@pytest.mark.asyncio
async def test_staff_route_not_cached(ds):
    response = await ds.client.get("/-/versions.json")
    assert response.headers["cache-control"] == "no-store"


# ------------------------------------------------- SQL permission surface


@pytest.mark.asyncio
async def test_arbitrary_sql_stays_denied_for_anonymous(ds):
    """The metadata machinery behind allow_sql / execute-sql is the area the
    0.65.3–0.65.5 security releases touched — the catalogue must stay closed
    to arbitrary SQL for anonymous users even on an owner-gated deployment."""
    response = await ds.client.get(
        "/news.json?sql=select+content_text+from+mlaw_news"
    )
    assert response.status_code == 403
    assert "SECRET" not in response.text


# ------------------------------------------------------------ html rendering


@pytest.mark.asyncio
async def test_database_index_page_renders_html(ds):
    response = await ds.client.get("/")
    assert response.status_code == 200
    assert response.text.lstrip().startswith("<!DOCTYPE html>")
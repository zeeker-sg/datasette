"""Shared pytest fixtures for zeeker-frontend tests."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def databases_fixture() -> dict:
    return _load_fixture("databases.json")


@pytest.fixture
def sglawwatch_fixture() -> dict:
    return _load_fixture("sglawwatch.json")


@pytest.fixture
def metadata_fixture() -> dict:
    return _load_fixture("metadata.json")


@pytest.fixture
def mock_datasette(databases_fixture, sglawwatch_fixture, metadata_fixture):
    """Returns an httpx.AsyncClient backed by MockTransport.

    Routes the 3 captured JSON fixtures based on path."""

    def _handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/.json":
            return httpx.Response(200, json=databases_fixture)
        if path == "/-/metadata.json":
            return httpx.Response(200, json=metadata_fixture)
        if path == "/sglawwatch.json":
            return httpx.Response(200, json=sglawwatch_fixture)
        # Default: 404 (matches datasette behavior for unknown db)
        return httpx.Response(
            404,
            json={"ok": False, "error": "Database not found", "status": 404, "title": None},
        )

    return httpx.AsyncClient(
        base_url="http://zeeker-datasette:8001",
        transport=httpx.MockTransport(_handler),
    )

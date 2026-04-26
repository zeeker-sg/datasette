"""Stub tests for the auxiliary HTML routes.

Real assertions land in Plan 06-03 (`/developers`, `/status`, `/sources`,
`/about`, `/how-to-use`, `/llms.txt`, `/robots.txt`). This file exists so
Plan 06-03 can drop test bodies onto pre-existing names without touching
the test inventory in the same commit as the handler implementation.

Each test currently calls `pytest.skip(...)` with a message citing the
plan number that will fill in the body. The file is pytest-collectable
(`uv run pytest --collect-only` exits 0) and contains no imports of the
yet-to-exist `zeeker_frontend.routes_aux` module.
"""

from __future__ import annotations

import pytest


def test_developers_renders():
    pytest.skip("Implementation pending - Plan 06-03")


def test_status_renders():
    pytest.skip("Implementation pending - Plan 06-03")


def test_sources_hides_internal():
    pytest.skip("Implementation pending - Plan 06-03")


def test_about_renders():
    pytest.skip("Implementation pending - Plan 06-03")


def test_how_to_use_re_pointed():
    pytest.skip("Implementation pending - Plan 06-03")


def test_llms_txt_format():
    pytest.skip("Implementation pending - Plan 06-03")


def test_robots_txt():
    pytest.skip("Implementation pending - Plan 06-03")

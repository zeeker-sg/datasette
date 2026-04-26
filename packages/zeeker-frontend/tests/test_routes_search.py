"""Stub tests for the cross-database `/search` route.

Real assertions land in Plan 06-04 (the FTS fan-out handler). This file
asserts only that the test names exist and are pytest-collectable; the
plan that wires `routes_search.py` will replace the `pytest.skip` bodies
with real assertions against the fixtures created by Plan 06-01.

No imports of `zeeker_frontend.routes_search` here -- that module is
authored by Plan 06-04.
"""

from __future__ import annotations

import pytest


def test_search_empty_query():
    pytest.skip("Implementation pending - Plan 06-04")


def test_search_groups_results():
    pytest.skip("Implementation pending - Plan 06-04")


def test_search_partial_failure():
    pytest.skip("Implementation pending - Plan 06-04")


def test_search_503_empty_cache():
    pytest.skip("Implementation pending - Plan 06-04")


def test_search_xss_q_echoed():
    pytest.skip("Implementation pending - Plan 06-04")

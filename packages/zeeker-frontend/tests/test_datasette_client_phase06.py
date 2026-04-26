"""Stub unit tests for the new datasette_client helpers added in Phase 6.

The three helpers -- `discover_searchable_tables`, `search_table`,
`execute_sql` -- ship in Plan 06-02. Real assertions for each test name
below land in Plan 06-02 alongside the helper implementation.

This file does NOT import the new helpers; Plan 06-02 adds those to
`zeeker_frontend.datasette_client` and replaces the skip bodies with
real assertions.
"""

from __future__ import annotations

import pytest


def test_discover_searchable_extracts_fts_table():
    pytest.skip("Implementation pending - Plan 06-02")


def test_discover_searchable_filters_zeeker_prefix():
    pytest.skip("Implementation pending - Plan 06-02")


def test_discover_searchable_filters_hidden():
    pytest.skip("Implementation pending - Plan 06-02")


def test_search_table_passes_q_and_size():
    pytest.skip("Implementation pending - Plan 06-02")


def test_search_table_404_returns_none():
    pytest.skip("Implementation pending - Plan 06-02")


def test_execute_sql_builds_param_url():
    pytest.skip("Implementation pending - Plan 06-02")


def test_execute_sql_400_returns_friendly_error():
    pytest.skip("Implementation pending - Plan 06-02")


def test_execute_sql_404_returns_db_not_found():
    pytest.skip("Implementation pending - Plan 06-02")


def test_execute_sql_shape_objects_always_set():
    pytest.skip("Implementation pending - Plan 06-02")

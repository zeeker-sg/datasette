"""Stub tests for the `/sql` and `/sql/{db}` routes.

Real assertions land in Plan 06-05 (the thin SQL editor). This file
exists so the planner can author assertions against pre-existing test
names; the GREEN bodies arrive with the handler implementation.

No imports of `zeeker_frontend.routes_sql` -- that module ships in Plan
06-05.
"""

from __future__ import annotations

import pytest


def test_sql_landing():
    pytest.skip("Implementation pending - Plan 06-05")


def test_sql_db_get():
    pytest.skip("Implementation pending - Plan 06-05")


def test_sql_db_post_success():
    pytest.skip("Implementation pending - Plan 06-05")


def test_sql_db_post_400_error():
    pytest.skip("Implementation pending - Plan 06-05")


def test_sql_db_truncation_banner():
    pytest.skip("Implementation pending - Plan 06-05")


def test_sql_db_export_links():
    pytest.skip("Implementation pending - Plan 06-05")


def test_detect_params_regex():
    pytest.skip("Implementation pending - Plan 06-05")

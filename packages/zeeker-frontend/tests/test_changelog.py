"""Stub tests for the boot-loaded changelog module.

The `zeeker_frontend.changelog` module ships in Plan 06-02 and exposes
`load_changelog() -> list[dict]`. Real assertions for each name below
land in Plan 06-02 alongside the loader implementation.

This file does NOT import `zeeker_frontend.changelog` -- the module
arrives in Plan 06-02. Until then the file is collectable but every
test is skipped.
"""

from __future__ import annotations

import pytest


def test_load_changelog_returns_list_of_dicts():
    pytest.skip("Implementation pending - Plan 06-02")


def test_load_changelog_returns_empty_when_file_missing():
    pytest.skip("Implementation pending - Plan 06-02")


def test_load_changelog_returns_empty_on_invalid_yaml():
    pytest.skip("Implementation pending - Plan 06-02")


def test_load_changelog_filters_entries_without_date():
    pytest.skip("Implementation pending - Plan 06-02")

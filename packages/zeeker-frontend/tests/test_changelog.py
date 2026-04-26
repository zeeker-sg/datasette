"""Unit tests for the boot-loaded changelog YAML loader.

Pattern: `tmp_path` fixture writes a synthetic changelog.yaml; monkeypatch
swaps the module-level `_DATA_DIR` constant so each test exercises the
loader in isolation. Mirrors RESEARCH §Pattern 3.
"""

from __future__ import annotations

from zeeker_frontend.changelog import load_changelog


def test_load_changelog_returns_list_of_dicts(tmp_path, monkeypatch):
    yaml_file = tmp_path / "changelog.yaml"
    yaml_file.write_text(
        "recent_updates:\n"
        "  - date: '2025-06-09'\n"
        "    type: feature\n"
        "    title: Launch\n"
        "    description: hi\n"
    )
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    items = load_changelog()
    assert len(items) == 1
    assert items[0]["date"] == "2025-06-09"
    assert items[0]["type"] == "feature"
    assert items[0]["title"] == "Launch"


def test_load_changelog_returns_empty_when_file_missing(tmp_path, monkeypatch):
    # tmp_path has no changelog.yaml inside it
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    assert load_changelog() == []


def test_load_changelog_returns_empty_on_invalid_yaml(tmp_path, monkeypatch):
    (tmp_path / "changelog.yaml").write_text("!!!not valid yaml: [ unbalanced")
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    assert load_changelog() == []


def test_load_changelog_filters_entries_without_date(tmp_path, monkeypatch):
    yaml_file = tmp_path / "changelog.yaml"
    yaml_file.write_text(
        "recent_updates:\n"
        "  - date: '2025-06-09'\n"
        "    type: feature\n"
        "    title: Good entry\n"
        "  - type: bugfix\n"
        "    title: Missing date — drop me\n"
        "  - 'just-a-string'\n"  # not a dict — drop
    )
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    items = load_changelog()
    assert len(items) == 1
    assert items[0]["title"] == "Good entry"


def test_load_changelog_sorts_by_date_descending(tmp_path, monkeypatch):
    """/status surface needs latest first regardless of YAML file order."""
    yaml_file = tmp_path / "changelog.yaml"
    yaml_file.write_text(
        "recent_updates:\n"
        "  - date: '2025-06-09'\n"
        "    title: oldest\n"
        "  - date: '2026-04-26'\n"
        "    title: newest\n"
        "  - date: '2026-04-21'\n"
        "    title: middle\n"
    )
    monkeypatch.setattr("zeeker_frontend.changelog._DATA_DIR", tmp_path)
    items = load_changelog()
    assert [i["title"] for i in items] == ["newest", "middle", "oldest"]

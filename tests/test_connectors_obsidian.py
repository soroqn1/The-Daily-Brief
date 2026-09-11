"""Tests for Obsidian connector."""

from pathlib import Path
from unittest.mock import patch

import pytest

from the_daily_brief.config import Config
from the_daily_brief.connectors.obsidian import ObsidianConnector


@pytest.mark.asyncio
async def test_obsidian_returns_empty_when_vault_missing(tmp_path: Path) -> None:
    """Test that missing vault path returns [] without raising."""
    missing_vault = tmp_path / "non_existent_vault"
    connector = ObsidianConnector(vault_path=missing_vault)
    items = await connector.fetch()
    assert items == []


@pytest.mark.asyncio
async def test_obsidian_returns_empty_when_disabled() -> None:
    """Test that connector returns [] when disabled in config."""
    dummy_config = Config(connectors={"obsidian": {"enabled": False}})
    with patch("the_daily_brief.connectors.obsidian.get_config", return_value=dummy_config):
        connector = ObsidianConnector()
        items = await connector.fetch()
        assert items == []


@pytest.mark.asyncio
async def test_obsidian_extracts_open_todos(tmp_path: Path) -> None:
    """Test extracting open tasks with correct categories and priorities."""
    vault = tmp_path / "test_vault"
    daily_dir = vault / "50 Daily"
    projects_dir = vault / "10 Projects"
    ignored_dir = vault / "60 Archive"
    hidden_dir = vault / "50 Daily" / ".obsidian"

    daily_dir.mkdir(parents=True)
    projects_dir.mkdir(parents=True)
    ignored_dir.mkdir(parents=True)
    hidden_dir.mkdir(parents=True)

    # Note in 50 Daily
    daily_note = daily_dir / "2026-09-12-daily.md"
    daily_note.write_text(
        """# Today
- [ ] Review pull requests
- [x] Morning coffee (completed)
  - [ ] Urgent: Deploy critical fix to production
- Regular bullet item
""",
        encoding="utf-8",
    )

    # Note in 10 Projects
    project_note = projects_dir / "brief_project.md"
    project_note.write_text(
        """# Brief Project
- [ ] Implement Jinja2 renderer
- [X] Setup git repo
""",
        encoding="utf-8",
    )

    # Note in ignored directory
    archive_note = ignored_dir / "old.md"
    archive_note.write_text("- [ ] Old archived task\n", encoding="utf-8")

    # Note in hidden directory
    hidden_note = hidden_dir / "hidden.md"
    hidden_note.write_text("- [ ] Hidden task\n", encoding="utf-8")

    connector = ObsidianConnector(vault_path=vault, scan_dirs=["50 Daily", "10 Projects"])
    items = await connector.fetch()

    assert len(items) == 3

    # Verify task titles
    titles = [item.title for item in items]
    assert "Review pull requests" in titles
    assert "Urgent: Deploy critical fix to production" in titles
    assert "Implement Jinja2 renderer" in titles
    assert "Old archived task" not in titles
    assert "Hidden task" not in titles
    assert "Morning coffee (completed)" not in titles

    # Verify priorities and properties
    urgent_item = next(i for i in items if "Urgent" in i.title)
    assert urgent_item.priority == 1
    assert urgent_item.category == "task"
    assert urgent_item.source == "obsidian"
    assert "obsidian://open?vault=test_vault" in (urgent_item.url or "")
    assert urgent_item.timestamp is not None

    normal_item = next(i for i in items if i.title == "Review pull requests")
    assert normal_item.priority == 2


@pytest.mark.asyncio
async def test_obsidian_unexpected_error_handled_gracefully(tmp_path: Path) -> None:
    """Test that unexpected errors return [] without raising."""
    vault = tmp_path / "broken_vault"
    vault.mkdir()
    connector = ObsidianConnector(vault_path=vault)

    with patch.object(Path, "rglob", side_effect=PermissionError("Permission denied")):
        items = await connector.fetch()
        assert items == []

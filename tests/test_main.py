"""Tests for the orchestrator in main.py."""

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from the_daily_brief.config import Config
from the_daily_brief.connectors.base import BriefItem
from the_daily_brief.main import (
    cleanup_old_briefs,
    discover_connectors,
    get_active_connectors,
    run,
)
from the_daily_brief.models import BriefData
from the_daily_brief.state import State


def test_discover_connectors() -> None:
    """Test discovering concrete connector classes in connectors package."""
    classes = discover_connectors()
    names = [getattr(c, "name", "") for c in classes]
    assert "gmail" in names
    assert "obsidian" in names


def test_get_active_connectors() -> None:
    """Test instantiating only connectors enabled in configuration."""
    config = Config(
        connectors={
            "gmail": {"enabled": True},
            "obsidian": {"enabled": False},
        }
    )
    active = get_active_connectors(config)
    active_names = [c.name for c in active]
    assert "gmail" in active_names
    assert "obsidian" not in active_names


def test_cleanup_old_briefs(tmp_path: Path) -> None:
    """Test removing briefs older than 7 days while keeping recent ones."""
    briefs_dir = tmp_path / "briefs"
    briefs_dir.mkdir()

    recent_file = briefs_dir / "recent.html"
    recent_file.write_text("recent", encoding="utf-8")

    old_file = briefs_dir / "old.html"
    old_file.write_text("old", encoding="utf-8")

    # Set mtime for old_file to 10 days ago
    ten_days_ago = (datetime.now() - timedelta(days=10)).timestamp()
    os.utime(old_file, (ten_days_ago, ten_days_ago))

    deleted = cleanup_old_briefs(briefs_dir, keep_days=7)
    assert deleted == 1
    assert recent_file.exists()
    assert not old_file.exists()


@pytest.mark.asyncio
async def test_run_skips_when_already_generated(tmp_path: Path) -> None:
    """Test orchestrator exits silently if brief already generated today."""
    dummy_config = Config(output_dir=tmp_path)
    mock_state = State(last_brief_date=date.today().isoformat())

    with (
        patch("the_daily_brief.main.get_config", return_value=dummy_config),
        patch("the_daily_brief.main.load_state", return_value=mock_state),
    ):
        result = await run(open_browser=False)
        assert result is None


@pytest.mark.asyncio
async def test_run_skips_when_too_early(tmp_path: Path) -> None:
    """Test orchestrator exits silently if before 09:00 cutoff."""
    dummy_config = Config(output_dir=tmp_path, brief_after_hour=10)
    mock_state = State(last_brief_date=None)

    with (
        patch("the_daily_brief.main.get_config", return_value=dummy_config),
        patch("the_daily_brief.main.load_state", return_value=mock_state),
        patch("the_daily_brief.main.too_early", return_value=True),
    ):
        result = await run(open_browser=False)
        assert result is None


@pytest.mark.asyncio
async def test_run_force_bypasses_cutoff(tmp_path: Path) -> None:
    """Test that force=True bypasses early hour and idempotency."""
    dummy_config = Config(output_dir=tmp_path)
    state_file = tmp_path / "state.json"
    dummy_config.ensure_directories()
    mock_state = State(last_brief_date=date.today().isoformat(), _path=state_file)

    mock_llm = AsyncMock()
    mock_llm.generate.return_value = BriefData(headline="Forced Brief")

    with (
        patch("the_daily_brief.main.get_config", return_value=dummy_config),
        patch("the_daily_brief.main.load_state", return_value=mock_state),
        patch("the_daily_brief.main.too_early", return_value=True),
        patch("the_daily_brief.main.get_active_connectors", return_value=[]),
        patch("the_daily_brief.main.get_llm_client", return_value=mock_llm),
    ):
        result = await run(open_browser=False, force=True)
        assert result is not None
        assert "Forced Brief" in result.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_run_llm_failure_triggers_notification(tmp_path: Path) -> None:
    """Test that LLM API failure triggers macOS notification and exits."""
    dummy_config = Config(output_dir=tmp_path, brief_after_hour=8)
    mock_state = State(last_brief_date=None)

    mock_llm = AsyncMock()
    mock_llm.generate.side_effect = RuntimeError("API rate limit exceeded")

    with (
        patch("the_daily_brief.main.get_config", return_value=dummy_config),
        patch("the_daily_brief.main.load_state", return_value=mock_state),
        patch("the_daily_brief.main.too_early", return_value=False),
        patch("the_daily_brief.main.get_active_connectors", return_value=[]),
        patch("the_daily_brief.main.get_llm_client", return_value=mock_llm),
        patch("the_daily_brief.main.notify") as mock_notify,
    ):
        result = await run(open_browser=False)
        assert result is None
        mock_notify.assert_called_once()
        assert "API rate limit exceeded" in mock_notify.call_args[1]["message"]


@pytest.mark.asyncio
async def test_run_success_flow(tmp_path: Path) -> None:
    """Test complete successful generation flow."""
    dummy_config = Config(output_dir=tmp_path, brief_after_hour=8)
    state_file = tmp_path / "state.json"
    dummy_config.ensure_directories()
    mock_state = State(last_brief_date=None, _path=state_file)

    mock_connector = AsyncMock()
    mock_connector.name = "mock"
    mock_connector.fetch.return_value = [
        BriefItem(source="mock", category="task", title="Task 1", body="Do it", priority=1)
    ]

    mock_brief_data = BriefData(
        headline="Great Success",
        ai_recommendation="Keep going",
    )
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = mock_brief_data

    with (
        patch("the_daily_brief.main.get_config", return_value=dummy_config),
        patch("the_daily_brief.main.load_state", return_value=mock_state),
        patch("the_daily_brief.main.too_early", return_value=False),
        patch("the_daily_brief.main.get_active_connectors", return_value=[mock_connector]),
        patch("the_daily_brief.main.get_llm_client", return_value=mock_llm),
    ):
        brief_path = await run(open_browser=False)
        assert brief_path is not None
        assert brief_path.is_file()
        assert "Great Success" in brief_path.read_text(encoding="utf-8")
        assert mock_state.brief_generated_today is True

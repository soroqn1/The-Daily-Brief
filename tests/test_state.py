"""Tests for state management."""

from datetime import date, datetime
from pathlib import Path

from the_daily_brief.state import load_state, too_early


def test_too_early() -> None:
    """Test cutoff time check."""
    early_time = datetime(2026, 9, 12, 8, 30)
    exact_time = datetime(2026, 9, 12, 9, 0)
    late_time = datetime(2026, 9, 12, 10, 15)

    assert too_early(cutoff_hour=9, now=early_time) is True
    assert too_early(cutoff_hour=9, now=exact_time) is False
    assert too_early(cutoff_hour=9, now=late_time) is False


def test_state_defaults_when_missing(tmp_path: Path) -> None:
    """Test loading state when file does not exist."""
    state_file = tmp_path / "state.json"
    state = load_state(path=state_file)

    assert state.last_brief_date is None
    assert state.brief_generated_today is False


def test_state_mark_done_and_reload(tmp_path: Path) -> None:
    """Test marking state done and reloading from file."""
    state_file = tmp_path / "state.json"
    state = load_state(path=state_file)

    today = date.today()
    state.mark_done(today)

    assert state.brief_generated_today is True
    assert state.last_brief_date == today.isoformat()

    # Verify reloading from disk
    reloaded = load_state(path=state_file)
    assert reloaded.brief_generated_today is True
    assert reloaded.last_brief_date == today.isoformat()


def test_corrupt_state_file_handled_gracefully(tmp_path: Path) -> None:
    """Test corrupt JSON in state file produces a fresh State."""
    state_file = tmp_path / "state.json"
    state_file.write_text("not json content", encoding="utf-8")

    state = load_state(path=state_file)
    assert state.last_brief_date is None
    assert state.brief_generated_today is False

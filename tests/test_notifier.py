"""Tests for macOS notifier."""

import subprocess
from unittest.mock import patch

from the_daily_brief.notifier import notify


def test_notify_success() -> None:
    """Test successful osascript execution."""
    mock_res = subprocess.CompletedProcess(args=["osascript"], returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=mock_res) as mock_run:
        delivered = notify("Brief ready", title="The Daily Brief", subtitle="Good morning")
        assert delivered is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "display notification" in cmd[2]
        assert "Brief ready" in cmd


def test_notify_failure_status() -> None:
    """Test non-zero exit code from osascript."""
    mock_res = subprocess.CompletedProcess(
        args=["osascript"], returncode=1, stdout="", stderr="Error"
    )
    with patch("subprocess.run", return_value=mock_res):
        delivered = notify("Brief failed")
        assert delivered is False


def test_notify_exception_handling() -> None:
    """Test handling unexpected exceptions gracefully."""
    with patch("subprocess.run", side_effect=OSError("Command not found")):
        delivered = notify("Hello")
        assert delivered is False

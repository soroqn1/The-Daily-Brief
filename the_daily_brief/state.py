"""State management for The Daily Brief."""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from the_daily_brief.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class State:
    last_brief_date: str | None = None
    reports: dict[str, str] = field(default_factory=dict)
    _path: Path | None = None

    @property
    def brief_generated_today(self) -> bool:
        """Return True if a brief has already been generated today."""
        if not self.last_brief_date:
            return False
        return self.last_brief_date == date.today().isoformat()

    def is_generated_today(self, space: str, report_type: str) -> bool:
        """Check if a specific report has been generated today for a space."""
        key = f"{space}:{report_type}"
        return self.reports.get(key) == date.today().isoformat()

    def mark_done(
        self,
        brief_date: date | None = None,
        space: str = "default",
        report_type: str = "daily",
    ) -> None:
        """Mark report as completed and persist state."""
        target_date = brief_date if brief_date is not None else date.today()
        self.last_brief_date = target_date.isoformat()
        self.reports[f"{space}:{report_type}"] = target_date.isoformat()
        save_state(self, self._path)


def load_state(path: Path | None = None) -> State:
    """Load state from state.json, or return a default State if missing or invalid."""
    state_path = path if path is not None else get_config().state_file
    if not state_path.is_file():
        return State(_path=state_path)

    try:
        with open(state_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return State(
                last_brief_date=data.get("last_brief_date"),
                reports=data.get("reports", {}),
                _path=state_path,
            )
    except Exception:
        logger.warning(
            "Failed to read state file at %s, returning fresh state",
            state_path,
            exc_info=True,
        )
        return State(_path=state_path)


def save_state(state: State, path: Path | None = None) -> None:
    """Save state to JSON file atomically."""
    state_path = path if path is not None else (state._path or get_config().state_file)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_brief_date": state.last_brief_date,
        "reports": state.reports,
    }
    tmp_path = state_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, state_path)

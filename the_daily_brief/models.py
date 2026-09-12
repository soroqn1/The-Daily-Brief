"""Data models for The Daily Brief."""

from dataclasses import asdict, dataclass, field
from typing import Any

from the_daily_brief.connectors.base import BriefItem


@dataclass
class BriefData:
    """Structured data returned by LLM and passed to HTML renderer.

    Items are grouped into 4 fixed sections:
    1. action_required: Unanswered emails, urgent tasks, mentions
    2. missed: Emails, messages, notifications received overnight
    3. schedule: Calendar events sorted by time
    4. tasks: Open tasks, goals, and project TODOs

    Each item is a dictionary with:
    - title: str
    - summary: str (optional 1-2 line summary)
    - source: str (e.g. 'gmail', 'gmail · work', 'obsidian', 'calendar')
    - urgent: bool (optional flag for red accent badge)
    - url: str (optional deep link)
    - time: str (optional for schedule items)
    - status: str (optional for tasks, e.g. 'open')
    """

    headline: str = ""
    action_required: list[dict[str, Any]] = field(default_factory=list)
    missed: list[dict[str, Any]] = field(default_factory=list)
    schedule: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    ai_recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert BriefData to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BriefData":
        """Create BriefData from dictionary safely."""
        return cls(
            headline=str(data.get("headline", "")),
            action_required=list(data.get("action_required", [])),
            missed=list(data.get("missed", [])),
            schedule=list(data.get("schedule", [])),
            tasks=list(data.get("tasks", [])),
            ai_recommendation=str(data.get("ai_recommendation", "")),
        )


__all__ = ["BriefData", "BriefItem"]

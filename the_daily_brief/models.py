"""Data models for The Daily Brief."""

from dataclasses import asdict, dataclass, field
from typing import Any

from the_daily_brief.connectors.base import BriefItem


@dataclass
class BriefData:
    """Structured data returned by LLM and passed to HTML renderer."""

    headline: str = ""
    missed: list[dict[str, Any]] = field(default_factory=list)
    action_required: list[dict[str, Any]] = field(default_factory=list)
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
            missed=list(data.get("missed", [])),
            action_required=list(data.get("action_required", [])),
            schedule=list(data.get("schedule", [])),
            tasks=list(data.get("tasks", [])),
            ai_recommendation=str(data.get("ai_recommendation", "")),
        )


__all__ = ["BriefData", "BriefItem"]

"""Base connector contract and BriefItem data structure."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BriefItem:
    """Universal item emitted by connectors."""

    source: str
    category: str
    title: str
    body: str
    priority: int
    timestamp: datetime | None = None
    url: str | None = None


class BaseConnector(ABC):
    """Abstract base class that all data connectors must implement."""

    name: str

    @abstractmethod
    async def fetch(self) -> list[BriefItem]:
        """Fetch items since the last brief timestamp.

        NEVER raises — catch all exceptions, log them, return [].
        """

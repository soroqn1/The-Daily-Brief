"""Base contract for LLM clients."""

from abc import ABC, abstractmethod

from the_daily_brief.models import BriefData, BriefItem, EmailAuditData


class BaseLLMClient(ABC):
    """Abstract base class for all LLM provider clients."""

    @abstractmethod
    async def generate(self, items: list[BriefItem]) -> BriefData:
        """Single API call. Returns structured BriefData JSON."""

    @abstractmethod
    async def generate_email_audit(self, items: list[BriefItem]) -> EmailAuditData:
        """Single API call for email audit. Returns structured EmailAuditData JSON."""

"""Connectors package for data sources."""

from the_daily_brief.connectors.base import BaseConnector, BriefItem
from the_daily_brief.connectors.gmail import GmailConnector

__all__ = ["BaseConnector", "BriefItem", "GmailConnector"]

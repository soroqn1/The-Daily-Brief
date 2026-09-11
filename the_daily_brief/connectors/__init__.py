"""Connectors package for data sources."""

from the_daily_brief.connectors.base import BaseConnector, BriefItem
from the_daily_brief.connectors.gmail import GmailConnector
from the_daily_brief.connectors.obsidian import ObsidianConnector

__all__ = ["BaseConnector", "BriefItem", "GmailConnector", "ObsidianConnector"]

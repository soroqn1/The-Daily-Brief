"""Dynamic registry for connector types and their configuration metadata."""

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from the_daily_brief.connectors.base import BaseConnector


@dataclass
class ConnectorTypeInfo:
    """Metadata and factory for a connector type."""

    type_id: str
    name: str
    description: str
    guide_url: str
    guide_steps: list[str] = field(default_factory=list)
    fields: list[dict[str, Any]] = field(default_factory=list)
    factory: Callable[[dict[str, Any]], BaseConnector] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for UI rendering."""
        rendered_fields: list[dict[str, Any]] = []
        for f in self.fields:
            item = dict(f)
            if item.get("name") == "client_id" and not item.get("default"):
                item["default"] = os.getenv("GMAIL_CLIENT_ID", "")
            elif item.get("name") == "client_secret" and not item.get("default"):
                item["default"] = os.getenv("GMAIL_CLIENT_SECRET", "")
            rendered_fields.append(item)

        return {
            "type_id": self.type_id,
            "name": self.name,
            "description": self.description,
            "guide_url": self.guide_url,
            "guide_steps": self.guide_steps,
            "fields": rendered_fields,
        }


_REGISTRY: dict[str, ConnectorTypeInfo] = {}


def register_connector_type(info: ConnectorTypeInfo) -> None:
    """Register a new connector type."""
    _REGISTRY[info.type_id] = info


def get_connector_type(type_id: str) -> ConnectorTypeInfo | None:
    """Retrieve connector metadata by type ID."""
    return _REGISTRY.get(type_id)


def list_connector_types() -> list[ConnectorTypeInfo]:
    """List all registered connector types."""
    return list(_REGISTRY.values())


def create_connector(type_id: str, config: dict[str, Any]) -> BaseConnector:
    """Instantiate a connector dynamically from its type and config."""
    info = get_connector_type(type_id)
    if not info or not info.factory:
        raise ValueError(f"Unknown connector type or missing factory: '{type_id}'")
    return info.factory(config)


# --- Register built-in connectors ---


def _gmail_factory(cfg: dict[str, Any]) -> BaseConnector:
    from the_daily_brief.connectors.gmail import GmailConnector

    def _parse_int(val: Any) -> int | None:
        if val is None or val == "":
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    return GmailConnector(
        client_id=cfg.get("client_id") or os.getenv("GMAIL_CLIENT_ID"),
        client_secret=cfg.get("client_secret") or os.getenv("GMAIL_CLIENT_SECRET"),
        refresh_token=cfg.get("refresh_token"),
        token_env=cfg.get("token_env", "GMAIL_REFRESH_TOKEN"),
        space_name=cfg.get("space_name", "default"),
        scan_hours=_parse_int(cfg.get("scan_hours")),
        audit_days=_parse_int(cfg.get("audit_days")),
        max_emails=_parse_int(cfg.get("max_emails")),
    )


register_connector_type(
    ConnectorTypeInfo(
        type_id="gmail",
        name="Gmail",
        description="Scans unread, flagged, and actionable emails via Gmail API.",
        guide_url="https://console.cloud.google.com/apis/credentials",
        guide_steps=[
            "Go to Google Cloud Console and enable Gmail API.",
            "Create OAuth 2.0 Desktop credentials (Client ID & Client Secret).",
            "Fill in Client ID & Secret below, then authorize or paste token.",
        ],
        fields=[
            {
                "name": "client_id",
                "label": "Client ID",
                "type": "text",
                "placeholder": "e.g. 185637645011-...apps.googleusercontent.com",
            },
            {
                "name": "client_secret",
                "label": "Client Secret",
                "type": "password",
                "placeholder": "e.g. GOCSPX-...",
            },
            {
                "name": "refresh_token",
                "label": "Refresh Token",
                "type": "password",
                "placeholder": "Paste token or click 'Authorize with Google' below",
            },
            {
                "name": "scan_hours",
                "label": "Daily Scan Window (hours)",
                "type": "number",
                "default": 12,
            },
            {
                "name": "audit_days",
                "label": "Email Audit Window (days)",
                "type": "number",
                "default": 5,
            },
            {
                "name": "max_emails",
                "label": "Max Emails to Scan",
                "type": "number",
                "default": 20,
            },
        ],
        factory=_gmail_factory,
    )
)


def _obsidian_factory(cfg: dict[str, Any]) -> BaseConnector:
    from the_daily_brief.connectors.obsidian import ObsidianConnector

    scan_dirs = cfg.get("scan_dirs")
    if isinstance(scan_dirs, str):
        scan_dirs = [s.strip() for s in scan_dirs.split(",") if s.strip()]

    return ObsidianConnector(
        vault_path=cfg.get("vault_path"),
        scan_dirs=scan_dirs or ["50 Daily", "10 Projects"],
    )


register_connector_type(
    ConnectorTypeInfo(
        type_id="obsidian",
        name="Obsidian Vault",
        description="Pulls open tasks, goals, and daily notes from your local Obsidian vault.",
        guide_url="https://obsidian.md",
        guide_steps=[
            "Locate your local Obsidian vault directory (e.g. ~/me/obsidian).",
            "Specify the folders to scan for TODOs and project files.",
        ],
        fields=[
            {
                "name": "vault_path",
                "label": "Vault Path",
                "type": "text",
                "default": "~/me/obsidian",
                "placeholder": "~/me/obsidian",
            },
            {
                "name": "scan_dirs",
                "label": "Scan Folders (comma separated)",
                "type": "text",
                "default": "50 Daily, 10 Projects",
                "placeholder": "50 Daily, 10 Projects",
            },
        ],
        factory=_obsidian_factory,
    )
)

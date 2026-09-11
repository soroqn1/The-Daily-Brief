"""Obsidian connector for extracting open TODOs and tasks from markdown vault notes."""

import logging
import os
import re
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

from the_daily_brief.config import get_config
from the_daily_brief.connectors.base import BaseConnector, BriefItem

logger = logging.getLogger(__name__)

TODO_PATTERN = re.compile(r"^\s*-\s*\[ \]\s+(.+)$", re.MULTILINE)
URGENT_KEYWORDS = ("urgent", "asap", "p0", "p1", "important", "high priority")


class ObsidianConnector(BaseConnector):
    """Connector for Obsidian markdown vaults."""

    name: str = "obsidian"

    def __init__(
        self,
        vault_path: str | Path | None = None,
        scan_dirs: list[str] | None = None,
    ) -> None:
        self._custom_vault_path = Path(vault_path) if vault_path else None
        self._custom_scan_dirs = scan_dirs

    def _resolve_vault_path(self, configured_path: str | None) -> Path | None:
        """Resolve and validate the vault directory path."""
        raw_path = self._custom_vault_path or configured_path or "~/me/obsidian"
        vault = Path(os.path.expanduser(str(raw_path)))
        if not vault.is_dir():
            logger.warning("Obsidian vault directory not found at: %s", vault)
            return None
        return vault

    async def fetch(self) -> list[BriefItem]:
        """Scan configured directories in Obsidian vault for open tasks.

        Never raises — logs exceptions and returns [].
        """
        try:
            config = get_config()
            obsidian_cfg = config.connectors.get("obsidian", {})
            if not obsidian_cfg.get("enabled", True):
                logger.debug("Obsidian connector is disabled in configuration.")
                return []

            vault_path = self._resolve_vault_path(obsidian_cfg.get("vault_path"))
            if vault_path is None:
                return []

            scan_dirs = (
                self._custom_scan_dirs
                if self._custom_scan_dirs is not None
                else obsidian_cfg.get("scan_dirs", ["50 Daily", "10 Projects"])
            )

            items: list[BriefItem] = []
            vault_name = vault_path.name

            for rel_dir in scan_dirs:
                target_dir = vault_path / rel_dir
                if not target_dir.is_dir():
                    logger.debug("Scan directory does not exist: %s", target_dir)
                    continue

                for file_path in target_dir.rglob("*.md"):
                    # Skip hidden directories like .obsidian, .trash, .git
                    rel_parts = file_path.relative_to(vault_path).parts
                    if any(part.startswith(".") for part in rel_parts):
                        continue

                    try:
                        content = file_path.read_text(encoding="utf-8")
                    except Exception as err:
                        logger.warning("Failed reading Obsidian file %s: %s", file_path, err)
                        continue

                    matches = TODO_PATTERN.findall(content)
                    if not matches:
                        continue

                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
                    rel_file = file_path.relative_to(vault_path).as_posix()
                    file_uri = urllib.parse.quote(rel_file)
                    obsidian_url = (
                        f"obsidian://open?vault={urllib.parse.quote(vault_name)}&file={file_uri}"
                    )

                    for match in matches:
                        task_text = match.strip()
                        if not task_text:
                            continue

                        # Check for urgency signals
                        lower_text = task_text.lower()
                        is_urgent = any(kw in lower_text for kw in URGENT_KEYWORDS)
                        priority = 1 if is_urgent else 2

                        items.append(
                            BriefItem(
                                source=self.name,
                                category="task",
                                title=task_text,
                                body=f"Note: {rel_file}",
                                priority=priority,
                                timestamp=mtime,
                                url=obsidian_url,
                            )
                        )

            return items

        except Exception as exc:
            logger.error("Unexpected error in Obsidian connector: %s", exc, exc_info=True)
            return []

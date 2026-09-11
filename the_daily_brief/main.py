"""Orchestrator for The Daily Brief."""

import asyncio
import importlib
import inspect
import logging
import pkgutil
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path

import the_daily_brief.connectors
from the_daily_brief.config import Config, get_config
from the_daily_brief.connectors.base import BaseConnector, BriefItem
from the_daily_brief.llm import get_llm_client
from the_daily_brief.notifier import notify
from the_daily_brief.renderer import render_brief
from the_daily_brief.state import load_state, too_early

logger = logging.getLogger(__name__)


def discover_connectors() -> list[type[BaseConnector]]:
    """Discover all concrete BaseConnector implementations in the connectors package."""
    connector_classes: list[type[BaseConnector]] = []
    package = the_daily_brief.connectors

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        if module_name == "base":
            continue
        full_module_name = f"{package.__name__}.{module_name}"
        module = importlib.import_module(full_module_name)
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseConnector) and obj is not BaseConnector:
                if obj not in connector_classes:
                    connector_classes.append(obj)

    return connector_classes


def get_active_connectors(config: Config) -> list[BaseConnector]:
    """Instantiate connectors that are enabled in configuration."""
    active: list[BaseConnector] = []
    for cls in discover_connectors():
        name = getattr(cls, "name", "")
        cfg = config.connectors.get(name, {})
        if isinstance(cfg, dict) and cfg.get("enabled", False):
            try:
                active.append(cls())
            except Exception as err:
                logger.warning("Failed to initialize connector %s: %s", name, err)
    return active


def cleanup_old_briefs(briefs_dir: Path, keep_days: int = 7) -> int:
    """Delete briefs older than keep_days days. Returns count of deleted files."""
    if not briefs_dir.is_dir():
        return 0

    now = datetime.now()
    cutoff = now - timedelta(days=keep_days)
    deleted_count = 0

    for html_file in briefs_dir.glob("*.html"):
        try:
            mtime = datetime.fromtimestamp(html_file.stat().st_mtime)
            if mtime < cutoff:
                html_file.unlink()
                deleted_count += 1
                logger.debug("Deleted old brief: %s", html_file)
        except Exception as err:
            logger.warning("Failed to remove old brief %s: %s", html_file, err)

    return deleted_count


async def run(open_browser: bool = True, force: bool = False) -> Path | None:
    """Run the daily brief pipeline."""
    config = get_config()
    config.ensure_directories()
    state = load_state(config.state_file)

    if not force:
        if state.brief_generated_today:
            logger.info("Brief already generated today. Exiting.")
            return None

        if too_early(config.brief_after_hour):
            logger.info(
                "Current time is before %02d:00 cutoff. Exiting.",
                config.brief_after_hour,
            )
            return None

    logger.info("Starting The Daily Brief generation...")

    active_connectors = get_active_connectors(config)
    logger.info("Discovered %d active connector(s)", len(active_connectors))

    results = await asyncio.gather(
        *[c.fetch() for c in active_connectors],
        return_exceptions=True,
    )

    all_items: list[BriefItem] = []
    for connector, res in zip(active_connectors, results, strict=False):
        if isinstance(res, list):
            all_items.extend(res)
        else:
            logger.warning("Connector '%s' failed: %s", connector.name, res)

    logger.info("Gathered %d total items from connectors", len(all_items))

    try:
        llm_client = get_llm_client(config.llm.provider)
        brief_data = await llm_client.generate(all_items)
    except Exception as exc:
        logger.error("LLM API failure: %s", exc, exc_info=True)
        notify(
            message=f"Failed to generate brief: {exc}",
            title="The Daily Brief",
            subtitle="LLM Generation Failure",
        )
        return None

    html_content = render_brief(brief_data)

    today_str = date.today().isoformat()
    brief_path = config.briefs_dir / f"{today_str}.html"
    brief_path.write_text(html_content, encoding="utf-8")
    logger.info("Saved brief to %s", brief_path)

    state.mark_done()

    if open_browser:
        webbrowser.open(brief_path.as_uri())

    cleaned = cleanup_old_briefs(config.briefs_dir, keep_days=7)
    if cleaned > 0:
        logger.info("Cleaned up %d old brief(s)", cleaned)

    return brief_path


def main() -> None:
    """Main execution entry point."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    force = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(run(force=force))


if __name__ == "__main__":
    main()

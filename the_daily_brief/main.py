"""Orchestrator for The Daily Brief."""

import argparse
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
from the_daily_brief.models import BriefData
from the_daily_brief.notifier import notify
from the_daily_brief.renderer import (
    render_brief,
    render_brief_markdown,
    render_email_audit,
    render_email_audit_markdown,
)
from the_daily_brief.state import load_state

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


def get_connectors_for_space(config: Config, space_name: str) -> list[BaseConnector]:
    """Instantiate connectors configured for a space using the dynamic registry."""
    from the_daily_brief.connectors.registry import create_connector

    space_cfg = config.get_space(space_name)
    connectors: list[BaseConnector] = []

    for inst in space_cfg.connectors:
        if not inst.enabled:
            continue
        try:
            cfg = dict(inst.config)
            cfg.setdefault("space_name", space_name)
            conn = create_connector(inst.type, cfg)
            connectors.append(conn)
        except Exception as err:
            logger.warning(
                "Failed to initialize connector '%s' (%s) in space '%s': %s",
                inst.id,
                inst.type,
                space_name,
                err,
            )

    return connectors


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


async def generate_daily_brief(
    space_name: str = "default",
    force: bool = False,
    open_browser: bool = False,
) -> tuple[Path, Path] | None:
    """Generate daily brief for a space, saving both .html and .md files."""
    config = get_config()
    config.ensure_directories()
    state = load_state(config.state_file)

    target_dir = config.get_space_dir(space_name)
    html_path = target_dir / "daily.html"
    md_path = target_dir / "daily.md"

    if not force and html_path.is_file() and md_path.is_file():
        logger.info("Daily brief already exists for '%s' today: %s", space_name, html_path)
        if open_browser:
            webbrowser.open(html_path.as_uri())
        return html_path, md_path

    logger.info("Starting Daily Brief generation for space '%s'...", space_name)
    connectors = get_connectors_for_space(config, space_name)
    results = await asyncio.gather(
        *[c.fetch() for c in connectors],
        return_exceptions=True,
    )

    all_items: list[BriefItem] = []
    warnings: list[str] = []
    for connector, res in zip(connectors, results, strict=False):
        if isinstance(res, list):
            all_items.extend(res)
        else:
            logger.warning("Connector '%s' failed: %s", connector.name, res)
            warnings.append(f"{connector.name}: {res}")
        last_err = getattr(connector, "last_error", None)
        if last_err:
            warnings.append(f"{connector.name}: {last_err}")

    logger.info("Gathered %d total items for %s", len(all_items), space_name)

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

    # Save Markdown file
    md_content = render_brief_markdown(brief_data, space_name=space_name, warnings=warnings)
    md_path.write_text(md_content, encoding="utf-8")

    # Save HTML file
    html_content = render_brief(
        brief_data,
        file_path=str(md_path),
        space_name=space_name,
        warnings=warnings,
    )
    html_path.write_text(html_content, encoding="utf-8")

    # Also save to config.briefs_dir for archive
    today_str = date.today().isoformat()
    archive_brief = config.briefs_dir / f"{today_str}_{space_name}.html"
    archive_brief.write_text(html_content, encoding="utf-8")

    state.mark_done(space=space_name, report_type="daily")
    logger.info("Saved daily brief to %s and %s", html_path, md_path)

    if open_browser:
        webbrowser.open(html_path.as_uri())

    cleanup_old_briefs(config.briefs_dir, keep_days=7)
    return html_path, md_path


async def generate_email_audit(
    space_name: str = "default",
    force: bool = False,
    open_browser: bool = False,
) -> tuple[Path, Path] | None:
    """Generate deep email audit for a space, saving both .html and .md files."""
    config = get_config()
    config.ensure_directories()
    state = load_state(config.state_file)

    target_dir = config.get_space_dir(space_name)
    html_path = target_dir / "email.html"
    md_path = target_dir / "email.md"

    if not force and html_path.is_file() and md_path.is_file():
        logger.info("Email audit already exists for '%s' today: %s", space_name, html_path)
        if open_browser:
            webbrowser.open(html_path.as_uri())
        return html_path, md_path

    logger.info("Starting Email Audit for space '%s'...", space_name)
    space_cfg = config.get_space(space_name)
    connectors = get_connectors_for_space(config, space_name)
    audit_connectors = [c for c in connectors if hasattr(c, "fetch_audit")]
    if not audit_connectors:
        from the_daily_brief.connectors.gmail import GmailConnector

        audit_connectors = [
            GmailConnector(
                token_env=space_cfg.gmail_token_env,
                space_name=space_name,
            )
        ]

    tasks = [
        c.fetch_audit(
            days=space_cfg.gmail_audit_days,
            max_emails=space_cfg.gmail_max_emails,
        )
        for c in audit_connectors
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    items: list[BriefItem] = []
    warnings: list[str] = []
    for c, r in zip(audit_connectors, results, strict=False):
        if isinstance(r, list):
            items.extend(r)
        else:
            warnings.append(f"{getattr(c, 'name', 'Connector')}: {r}")
        last_err = getattr(c, "last_error", None)
        if last_err:
            warnings.append(f"{getattr(c, 'name', 'Connector').capitalize()}: {last_err}")
    logger.info("Gathered %d email items for audit in space '%s'", len(items), space_name)

    try:
        llm_client = get_llm_client(config.llm.provider)
        audit_data = await llm_client.generate_email_audit(items)
    except Exception as exc:
        logger.error("LLM API email audit failure: %s", exc, exc_info=True)
        notify(
            message=f"Failed to generate email audit: {exc}",
            title="The Daily Brief",
            subtitle="Email Audit Failure",
        )
        return None

    # Save Markdown file
    md_content = render_email_audit_markdown(audit_data, space_name=space_name)
    md_path.write_text(md_content, encoding="utf-8")

    # Save HTML file
    html_content = render_email_audit(
        audit_data,
        file_path=str(md_path),
        space_name=space_name,
    )
    html_path.write_text(html_content, encoding="utf-8")

    state.mark_done(space=space_name, report_type="email")
    logger.info("Saved email audit to %s and %s", html_path, md_path)

    if open_browser:
        webbrowser.open(html_path.as_uri())

    return html_path, md_path


async def generate_global_feed(
    force: bool = False,
    open_browser: bool = False,
) -> tuple[Path, Path] | None:
    """Generate Reddit-style unified feed across all spaces."""
    config = get_config()
    config.ensure_directories()

    target_dir = config.storage_dir / date.today().strftime("%d-%m-%y") / "global"
    target_dir.mkdir(parents=True, exist_ok=True)
    html_path = target_dir / "daily.html"
    md_path = target_dir / "daily.md"

    if not force and html_path.is_file() and md_path.is_file():
        logger.info("Global feed already exists today: %s", html_path)
        if open_browser:
            webbrowser.open(html_path.as_uri())
        return html_path, md_path

    spaces = list(config.spaces.keys()) if config.spaces else ["default"]
    feeds: list[tuple[str, BriefData]] = []

    for space_name in spaces:
        connectors = get_connectors_for_space(config, space_name)
        results = await asyncio.gather(*[c.fetch() for c in connectors], return_exceptions=True)
        items: list[BriefItem] = []
        for r in results:
            if isinstance(r, list):
                items.extend(r)

        try:
            llm_client = get_llm_client(config.llm.provider)
            b_data = await llm_client.generate(items)
            feeds.append((space_name, b_data))
        except Exception as err:
            logger.warning("Failed to generate brief for space '%s': %s", space_name, err)

    from the_daily_brief.renderer import render_global_feed, render_global_feed_markdown

    md_content = render_global_feed_markdown(feeds)
    md_path.write_text(md_content, encoding="utf-8")

    html_content = render_global_feed(feeds, file_path=str(md_path))
    html_path.write_text(html_content, encoding="utf-8")

    logger.info("Saved global feed to %s and %s", html_path, md_path)
    if open_browser:
        webbrowser.open(html_path.as_uri())

    return html_path, md_path


async def run(
    open_browser: bool = True,
    force: bool = False,
    space_name: str = "default",
    report_type: str = "daily",
) -> Path | None:
    """Run generation pipeline."""
    if space_name == "global" or report_type == "global":
        res = await generate_global_feed(force=force, open_browser=open_browser)
    elif report_type == "email":
        res = await generate_email_audit(
            space_name=space_name,
            force=force,
            open_browser=open_browser,
        )
    else:
        res = await generate_daily_brief(
            space_name=space_name,
            force=force,
            open_browser=open_browser,
        )

    return res[0] if res else None


def main() -> None:
    """Main execution entry point."""
    parser = argparse.ArgumentParser(
        description="The Daily Brief — On-demand morning brief and email audit."
    )
    parser.add_argument(
        "type",
        nargs="?",
        default="daily",
        choices=["daily", "email"],
        help="Report type: daily or email",
    )
    parser.add_argument(
        "--space", "-s", default="default", help="Space profile (e.g. default, work, study)"
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force regeneration even if already generated today",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not open report in browser")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(
        run(
            open_browser=not args.no_browser,
            force=args.force,
            space_name=args.space,
            report_type=args.type,
        )
    )


if __name__ == "__main__":
    main()

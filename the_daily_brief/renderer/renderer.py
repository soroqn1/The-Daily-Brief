"""Jinja2 HTML renderer for The Daily Brief."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from the_daily_brief.models import BriefData, EmailAuditData

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

SVG_ICONS: dict[str, str] = {
    "press_crest": (
        '<svg class="editorial-icon crest-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<rect x="3" y="3" width="18" height="18"/>'
        '<path d="M3 8.5h18M8.5 8.5v12.5M12 12.5h5M12 16h4"/>'
        '<circle cx="5.8" cy="5.8" r="0.9" fill="currentColor"/>'
        "</svg>"
    ),
    "sun": (
        '<svg class="editorial-icon theme-icon-day" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1'
        'M4.9 19.1l2.1-2.1M17 7l2.1-2.1"/>'
        "</svg>"
    ),
    "moon": (
        '<svg class="editorial-icon theme-icon-night" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>'
        '<polygon points="17 4 17.6 5.3 19 5.3 17.9 6.2 18.3 7.5 17 6.6 15.7 7.5 16.1 6.2 15 5.3 '
        '16.4 5.3" fill="currentColor"/>'
        "</svg>"
    ),
    "telegraph": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<path d="M12 2v20M7 8l5-5 5 5M4 14a11 11 0 0 1 0-8M20 6a11 11 0 0 1 0 8"/>'
        '<circle cx="12" cy="12" r="2" fill="currentColor"/>'
        "</svg>"
    ),
    "spark": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
        "</svg>"
    ),
    "quill": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<path d="M12 19l7-7 3 3-7 7-3-3z"/>'
        '<path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18"/>'
        '<path d="M2 2l7.5 7.5"/>'
        "</svg>"
    ),
    "rotary": (
        '<svg class="editorial-icon icon-rotary" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<path d="M21.5 2v6h-6"/>'
        '<path d="M21.3 15.6a10 10 0 1 1-.6-8.4l6.8-7.2"/>'
        '<circle cx="12" cy="12" r="2.5"/>'
        "</svg>"
    ),
    "open": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<path d="M7 17L17 7M7 7h10v10"/>'
        "</svg>"
    ),
    "trash": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<line x1="10" y1="11" x2="10" y2="17"/>'
        '<line x1="14" y1="11" x2="14" y2="17"/>'
        "</svg>"
    ),
    "clip": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<rect x="9" y="9" width="13" height="13"/>'
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
        "</svg>"
    ),
    "vault": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.8" stroke-linecap="square">'
        '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'
        "</svg>"
    ),
    "plus": (
        '<svg class="editorial-icon" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="square">'
        '<line x1="12" y1="5" x2="12" y2="19"/>'
        '<line x1="5" y1="12" x2="19" y2="12"/>'
        "</svg>"
    ),
}


def get_template_env() -> Environment:
    """Create and return Jinja2 environment configured for template rendering."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_brief(
    brief: BriefData,
    date_str: str | None = None,
    issue_number: str | None = None,
    file_path: str | None = None,
    space_name: str | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Render BriefData into a newspaper-style HTML document."""
    now = datetime.now()
    formatted_date = date_str or now.strftime("%A, %b %d")
    day_of_year = now.strftime("%j").lstrip("0") or "1"
    formatted_issue = issue_number or f"#{day_of_year}"

    env = get_template_env()
    template = env.get_template("brief.html.j2")

    return template.render(
        brief=brief,
        date_str=formatted_date,
        issue_number=formatted_issue,
        file_path=file_path,
        space_name=space_name or "default",
        warnings=warnings or [],
    )


def render_brief_markdown(
    brief: BriefData,
    space_name: str = "default",
    date_str: str | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Render BriefData to a clean Markdown document for AI/agent consumption."""
    formatted_date = date_str or datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 📰 The Daily Brief — {space_name.capitalize()} ({formatted_date})",
        "",
    ]
    if warnings:
        for w in warnings:
            lines.append(f"> ⚠️ **Warning**: {w}")
        lines.append("")

    if brief.headline:
        lines.append(f"> **{brief.headline}**")
    if brief.ai_recommendation:
        lines.append(f"> {brief.ai_recommendation}")
    lines.append("")

    if brief.action_required:
        lines.append("## ⚡ Action Required")
        for item in brief.action_required:
            title = item.get("title", "")
            summary = item.get("summary", "")
            source = item.get("source", "")
            url = item.get("url")
            link = f" [Open]({url})" if url else ""
            lines.append(f"- **{title}** ({source}): {summary}{link}")
        lines.append("")

    if brief.missed:
        lines.append("## 📬 Missed / Overnight")
        for item in brief.missed:
            title = item.get("title", "")
            summary = item.get("summary", "")
            source = item.get("source", "")
            url = item.get("url")
            link = f" [Open]({url})" if url else ""
            lines.append(f"- **{title}** ({source}): {summary}{link}")
        lines.append("")

    if brief.schedule:
        lines.append("## 📅 Schedule")
        for item in brief.schedule:
            t = item.get("time", "")
            title = item.get("title", "")
            lines.append(f"- **{t}**: {title}")
        lines.append("")

    if brief.tasks:
        lines.append("## 📝 Tasks & Goals")
        for item in brief.tasks:
            title = item.get("title", "")
            status = item.get("status", "open")
            check = " " if status == "open" else "x"
            lines.append(f"- [{check}] {title}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def render_email_audit(
    audit: EmailAuditData,
    date_str: str | None = None,
    file_path: str | None = None,
    space_name: str | None = None,
) -> str:
    """Render EmailAuditData into an HTML document."""
    now = datetime.now()
    formatted_date = date_str or now.strftime("%A, %b %d")

    env = get_template_env()
    template = env.get_template("email_audit.html.j2")

    return template.render(
        audit=audit,
        date_str=formatted_date,
        file_path=file_path,
        space_name=space_name or "default",
    )


def render_email_audit_markdown(
    audit: EmailAuditData,
    space_name: str = "default",
    date_str: str | None = None,
) -> str:
    """Render EmailAuditData to a clean Markdown document for AI/agent consumption."""
    formatted_date = date_str or datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 📬 Email Audit — {space_name.capitalize()} ({formatted_date})",
        "",
    ]
    if audit.headline:
        lines.append(f"> **{audit.headline}**")
    if audit.summary:
        lines.append(f"> {audit.summary}")
    lines.append("")

    if audit.needs_reply:
        lines.append("## ⚡ Needs Reply / Action")
        for item in audit.needs_reply:
            title = item.get("title", "")
            sender = item.get("sender", "")
            summary = item.get("summary", "")
            urgent = item.get("urgent", False)
            url = item.get("url")
            flag = " [URGENT]" if urgent else ""
            link = f" [Open]({url})" if url else ""
            lines.append(f"- **{title}** ({sender}){flag}: {summary}{link}")
        lines.append("")

    if audit.commitments_and_pending:
        lines.append("## ⏳ Commitments & In-Flight")
        for item in audit.commitments_and_pending:
            title = item.get("title", "")
            summary = item.get("summary", "")
            url = item.get("url")
            link = f" [Open]({url})" if url else ""
            lines.append(f"- **{title}**: {summary}{link}")
        lines.append("")

    if audit.deadlines_and_urgent:
        lines.append("## 📅 Deadlines & Urgent")
        for item in audit.deadlines_and_urgent:
            title = item.get("title", "")
            summary = item.get("summary", "")
            d = item.get("date", "")
            date_info = f" (Due: {d})" if d else ""
            url = item.get("url")
            link = f" [Open]({url})" if url else ""
            lines.append(f"- **{title}**{date_info}: {summary}{link}")
        lines.append("")

    if audit.checklist:
        lines.append("## ✅ Action Checklist")
        for task in audit.checklist:
            lines.append(f"- [ ] {task}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def render_global_feed(
    feeds: list[tuple[str, BriefData]],
    file_path: str | None = None,
    date_str: str | None = None,
) -> str:
    """Render unified Reddit-style global feed for all spaces."""
    now = datetime.now()
    formatted_date = date_str or now.strftime("%A, %b %d")

    env = get_template_env()
    template = env.get_template("global_feed.html.j2")

    return template.render(
        feeds=feeds,
        date_str=formatted_date,
        file_path=file_path,
    )


def render_global_feed_markdown(
    feeds: list[tuple[str, BriefData]],
    date_str: str | None = None,
) -> str:
    """Render unified Reddit-style global feed to Markdown."""
    formatted_date = date_str or datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 🌐 The Daily Brief — Global Feed ({formatted_date})",
        "",
        "> Aggregated timeline across all configured spaces.",
        "",
    ]

    for space_name, brief in feeds:
        lines.append(f"## ━━━ ◆ {space_name.upper()} ━━━")
        lines.append("")
        if brief.headline:
            lines.append(f'### "{brief.headline.strip('"')}"')
        if brief.ai_recommendation:
            lines.append(f"> {brief.ai_recommendation}")
        lines.append("")

        if brief.action_required:
            lines.append("#### ⚡ Action Required")
            for item in brief.action_required:
                title = item.get("title", "")
                summary = item.get("summary", "")
                source = item.get("source", "")
                url = item.get("url")
                link = f" [Open]({url})" if url else ""
                lines.append(f"- **{title}** ({source}): {summary}{link}")
            lines.append("")

        if brief.missed:
            lines.append("#### 📬 Overnight / Missed")
            for item in brief.missed:
                title = item.get("title", "")
                summary = item.get("summary", "")
                source = item.get("source", "")
                url = item.get("url")
                link = f" [Open]({url})" if url else ""
                lines.append(f"- **{title}** ({source}): {summary}{link}")
            lines.append("")

        if brief.tasks:
            lines.append("#### 📝 Tasks & Goals")
            for item in brief.tasks:
                title = item.get("title", "")
                status = item.get("status", "open")
                check = " " if status == "open" else "x"
                lines.append(f"- [{check}] {title}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def render_dashboard(
    config: Any,
    cards: list[dict[str, Any]],
    connector_types: list[dict[str, Any]],
    spaces_list: list[str],
    today_formatted: str,
) -> str:
    """Render hub settings dashboard."""
    env = get_template_env()
    template = env.get_template("dashboard.html.j2")
    return template.render(
        config=config,
        cards=cards,
        connector_types_json=json.dumps(connector_types),
        spaces_list_json=json.dumps(spaces_list),
        today_formatted=today_formatted,
        svg=SVG_ICONS,
    )

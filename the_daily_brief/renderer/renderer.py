"""Jinja2 HTML renderer for The Daily Brief."""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from the_daily_brief.models import BriefData

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


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
    )

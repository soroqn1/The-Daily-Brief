"""Tests for the HTML renderer and Jinja2 templates."""

from the_daily_brief.models import BriefData
from the_daily_brief.renderer import render_brief


def test_render_brief_basic() -> None:
    """Test rendering brief with full content."""
    brief = BriefData(
        headline="Major Product Launch and Critical Bugs",
        ai_recommendation="Fix production outage before attending meetings.",
        action_required=[
            {
                "title": "Production 500 Errors",
                "summary": "High error rate on API gateway",
                "source": "gmail",
                "url": "https://mail.google.com/mail/u/0/#inbox/123",
            }
        ],
        tasks=[
            {
                "title": "Review Q3 Roadmap",
                "summary": "Check priorities",
                "source": "obsidian",
                "url": "obsidian://open?vault=obsidian&file=50%20Daily%2Fnote.md",
            }
        ],
        missed=[
            {
                "title": "Team newsletter",
                "summary": "Weekly recap",
                "source": "gmail",
            }
        ],
        schedule=[
            {
                "time": "11:00 AM",
                "title": "Design Review",
                "source": "calendar",
            }
        ],
    )

    html = render_brief(brief, date_str="Saturday, September 12, 2026")

    # Font assertions
    assert "family=Playfair+Display" in html
    assert "family=Inter" in html

    # Content assertions
    assert "Major Product Launch and Critical Bugs" in html
    assert "Fix production outage before attending meetings." in html
    assert "Production 500 Errors" in html
    assert "https://mail.google.com/mail/u/0/#inbox/123" in html
    assert "Review Q3 Roadmap" in html
    obsidian_encoded = "obsidian://open?vault=obsidian&amp;file=50%20Daily%2Fnote.md"
    obsidian_raw = "obsidian://open?vault=obsidian&file=50%20Daily%2Fnote.md"
    assert (obsidian_encoded in html) or (obsidian_raw in html)
    assert "Team newsletter" in html
    assert "11:00 AM" in html
    assert "Urgent" in html


def test_render_brief_empty_state() -> None:
    """Test rendering brief when all categories are empty."""
    brief = BriefData(
        headline="Quiet Morning",
        ai_recommendation="Enjoy your coffee.",
    )

    html = render_brief(brief)
    assert "Quiet Morning" in html
    assert "Enjoy your coffee." in html
    assert "No urgent items requiring immediate action." in html
    assert "No open tasks recorded for today." in html
    assert "No unread or incoming updates." in html

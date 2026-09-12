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
                "source": "gmail_work",
                "urgent": True,
                "url": "https://mail.google.com/mail/u/0/#inbox/123",
            },
            {
                "title": "Invoice from Stripe",
                "summary": "Monthly billing ready",
                "source": "gmail",
                "urgent": False,
            },
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
        tasks=[
            {
                "title": "Review Q3 Roadmap",
                "summary": "Check priorities",
                "source": "obsidian",
                "url": "obsidian://open?vault=obsidian&file=50%20Daily%2Fnote.md",
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

    # Urgent badge and accent color
    assert "Urgent" in html
    assert "#c92a2a" in html

    # Source tags across different sources
    assert "[gmail · work]" in html
    assert "[gmail]" in html
    assert "[obsidian]" in html
    assert "[calendar]" in html

    # Order of 4 fixed sections:
    # Action Required -> Missed Overnight -> Today's Schedule -> Tasks & Goals
    pos_action = html.index("Action Required")
    pos_missed = html.index("Missed Overnight")
    pos_schedule = html.index("Today's Schedule")
    pos_tasks = html.index("Tasks & Goals")
    assert pos_action < pos_missed < pos_schedule < pos_tasks


def test_render_brief_empty_state() -> None:
    """Test rendering brief when all categories are empty: all 4 sections show 'All clear ✓'."""
    brief = BriefData(
        headline="Quiet Morning",
        ai_recommendation="Enjoy your coffee.",
    )

    html = render_brief(brief)
    assert "Quiet Morning" in html
    assert "Enjoy your coffee." in html

    # All 4 sections rendered in order even when empty
    pos_action = html.index("Action Required")
    pos_missed = html.index("Missed Overnight")
    pos_schedule = html.index("Today's Schedule")
    pos_tasks = html.index("Tasks & Goals")
    assert pos_action < pos_missed < pos_schedule < pos_tasks

    # Each empty section renders "All clear ✓"
    assert "All clear ✓" in html
    assert html.count("All clear ✓") == 4

"""Tests for email audit data model and rendering."""

from the_daily_brief.models import EmailAuditData
from the_daily_brief.renderer import (
    render_email_audit,
    render_email_audit_markdown,
)


def test_email_audit_model() -> None:
    """Test EmailAuditData instantiation and dict serialization."""
    audit = EmailAuditData(
        headline="Inbox Audit",
        summary="3 debts",
        needs_reply=[
            {
                "title": "Review PR",
                "sender": "alice@example.com",
                "summary": "Please review",
                "urgent": True,
                "url": "https://example.com/1",
            }
        ],
        commitments_and_pending=[{"title": "Send docs", "summary": "Waiting on draft"}],
        deadlines_and_urgent=[{"title": "Invoice due", "summary": "Pay it", "date": "Tomorrow"}],
        checklist=["Reply to Alice", "Pay invoice"],
    )

    data_dict = audit.to_dict()
    assert data_dict["headline"] == "Inbox Audit"
    assert len(data_dict["needs_reply"]) == 1

    restored = EmailAuditData.from_dict(data_dict)
    assert restored.headline == "Inbox Audit"
    assert restored.needs_reply[0]["sender"] == "alice@example.com"
    assert len(restored.checklist) == 2


def test_render_email_audit_markdown() -> None:
    """Test rendering EmailAuditData to Markdown."""
    audit = EmailAuditData(
        headline="Inbox Audit: 1 pending",
        summary="Clear inbox",
        needs_reply=[
            {
                "title": "Review PR",
                "sender": "alice@example.com",
                "summary": "Need signoff",
                "urgent": True,
                "url": "https://example.com/1",
            }
        ],
        checklist=["Reply to Alice"],
    )

    md = render_email_audit_markdown(audit, space_name="work", date_str="2026-09-20")
    assert "# 📬 Email Audit — Work (2026-09-20)" in md
    assert "> **Inbox Audit: 1 pending**" in md
    assert "## ⚡ Needs Reply / Action" in md
    assert "Review PR" in md
    assert "[URGENT]" in md
    assert "- [ ] Reply to Alice" in md


def test_render_email_audit_html() -> None:
    """Test rendering EmailAuditData to HTML."""
    audit = EmailAuditData(
        headline="Status Good",
        summary="All caught up",
        needs_reply=[],
        checklist=["Stay focused"],
    )

    html = render_email_audit(
        audit,
        space_name="study",
        file_path="/path/to/study/email.md",
        date_str="Sunday, Sep 20",
    )
    assert "Email Audit — Study" in html
    assert "/path/to/study/email.md" in html
    assert "Copy Path for AI" in html
    assert "Stay focused" in html

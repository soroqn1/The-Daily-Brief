"""Tests for BaseConnector ABC and BriefItem."""

from datetime import datetime

import pytest

from the_daily_brief.connectors.base import BaseConnector, BriefItem


def test_brief_item_instantiation() -> None:
    """Test creating BriefItem with required and optional fields."""
    now = datetime(2026, 9, 12, 8, 0)
    item = BriefItem(
        source="gmail",
        category="action_required",
        title="Urgent invoice",
        body="Please pay invoice #123",
        priority=1,
        timestamp=now,
        url="https://mail.google.com",
    )

    assert item.source == "gmail"
    assert item.category == "action_required"
    assert item.title == "Urgent invoice"
    assert item.body == "Please pay invoice #123"
    assert item.priority == 1
    assert item.timestamp == now
    assert item.url == "https://mail.google.com"


def test_brief_item_optional_defaults() -> None:
    """Test BriefItem default optional fields."""
    item = BriefItem(
        source="obsidian",
        category="task",
        title="Finish report",
        body="Draft the final quarter review",
        priority=2,
    )

    assert item.timestamp is None
    assert item.url is None


def test_base_connector_cannot_be_instantiated_directly() -> None:
    """Test that BaseConnector cannot be instantiated without fetch implementation."""
    with pytest.raises(TypeError):
        BaseConnector()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_concrete_connector_implementation() -> None:
    """Test concrete connector implementation conforming to BaseConnector contract."""

    class DummyConnector(BaseConnector):
        name = "dummy"

        async def fetch(self) -> list[BriefItem]:
            return [
                BriefItem(
                    source="dummy",
                    category="fyi",
                    title="Dummy Title",
                    body="Dummy Body",
                    priority=3,
                )
            ]

    connector = DummyConnector()
    assert connector.name == "dummy"
    items = await connector.fetch()
    assert len(items) == 1
    assert items[0].source == "dummy"

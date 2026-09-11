"""Tests for Gmail connector."""

from datetime import UTC, datetime
from unittest.mock import patch

import httpx
import pytest

from the_daily_brief.config import Config
from the_daily_brief.connectors.gmail import GmailConnector


@pytest.mark.asyncio
async def test_gmail_returns_empty_when_credentials_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that GmailConnector returns [] without error when credentials are not set."""
    monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)

    connector = GmailConnector()
    items = await connector.fetch()
    assert items == []


@pytest.mark.asyncio
async def test_gmail_returns_empty_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that GmailConnector returns [] when disabled in config."""
    monkeypatch.setenv("GMAIL_CLIENT_ID", "dummy_id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "dummy_secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "dummy_token")

    dummy_config = Config(connectors={"gmail": {"enabled": False}})
    with patch("the_daily_brief.connectors.gmail.get_config", return_value=dummy_config):
        connector = GmailConnector()
        items = await connector.fetch()
        assert items == []


@pytest.mark.asyncio
async def test_gmail_token_refresh_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test handling of OAuth token endpoint failure."""
    monkeypatch.setenv("GMAIL_CLIENT_ID", "dummy_id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "dummy_secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "dummy_token")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "oauth2.googleapis.com" in str(request.url):
            return httpx.Response(400, json={"error": "invalid_grant"})
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        connector = GmailConnector()
        items = await connector.fetch()
        assert items == []


@pytest.mark.asyncio
async def test_gmail_successful_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful message search and detail parsing."""
    monkeypatch.setenv("GMAIL_CLIENT_ID", "dummy_id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "dummy_secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "dummy_token")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "oauth2.googleapis.com" in url_str:
            return httpx.Response(200, json={"access_token": "mock_access_token"})

        if url_str.endswith("/messages") or "/messages?" in url_str:
            return httpx.Response(
                200,
                json={"messages": [{"id": "msg_1"}, {"id": "msg_2"}]},
            )

        if "/messages/msg_1" in url_str:
            return httpx.Response(
                200,
                json={
                    "id": "msg_1",
                    "snippet": "Urgent contract attached for review",
                    "internalDate": "1710000000000",
                    "labelIds": ["UNREAD", "STARRED"],
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Contract Review"},
                            {"name": "From", "value": "boss@company.com"},
                        ]
                    },
                },
            )

        if "/messages/msg_2" in url_str:
            return httpx.Response(
                200,
                json={
                    "id": "msg_2",
                    "snippet": "Weekly newsletter digest",
                    "internalDate": "1710000500000",
                    "labelIds": ["UNREAD"],
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Tech Weekly"},
                            {"name": "From", "value": "news@daily.com"},
                        ]
                    },
                },
            )

        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        connector = GmailConnector()
        items = await connector.fetch()

        assert len(items) == 2

        # msg_1 is STARRED -> priority 1, category "action_required"
        assert items[0].source == "gmail"
        assert items[0].category == "action_required"
        assert items[0].priority == 1
        assert "Contract Review" in items[0].title
        assert items[0].body == "Urgent contract attached for review"
        assert items[0].timestamp == datetime.fromtimestamp(1710000000, tz=UTC)
        assert items[0].url == "https://mail.google.com/mail/u/0/#inbox/msg_1"

        # msg_2 is unread only -> priority 2, category "missed"
        assert items[1].source == "gmail"
        assert items[1].category == "missed"
        assert items[1].priority == 2
        assert "Tech Weekly" in items[1].title


@pytest.mark.asyncio
async def test_gmail_network_exception_handled_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that unexpected network exceptions return [] without raising."""
    monkeypatch.setenv("GMAIL_CLIENT_ID", "dummy_id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "dummy_secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "dummy_token")

    def mock_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network is down")

    transport = httpx.MockTransport(mock_handler)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        connector = GmailConnector()
        items = await connector.fetch()
        assert items == []

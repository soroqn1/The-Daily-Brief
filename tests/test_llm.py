"""Tests for LLM clients and data models."""

import json
from unittest.mock import patch

import httpx
import pytest

from the_daily_brief.connectors.base import BriefItem
from the_daily_brief.llm import (
    GeminiClient,
    OpenAIClient,
    get_llm_client,
    test_llm_connection,
)
from the_daily_brief.models import BriefData


def test_brief_data_serialization() -> None:
    """Test BriefData conversion to and from dictionary."""
    data = {
        "headline": "A busy day ahead",
        "missed": [{"title": "Email 1", "summary": "Urgent", "source": "gmail"}],
        "action_required": [{"title": "Invoice", "summary": "$500", "source": "gmail"}],
        "schedule": [{"time": "10:00", "title": "Standup", "source": "calendar"}],
        "tasks": [{"title": "Clean vault", "status": "open", "source": "obsidian"}],
        "ai_recommendation": "Review invoice first",
    }
    brief = BriefData.from_dict(data)
    assert brief.headline == "A busy day ahead"
    assert len(brief.missed) == 1
    assert len(brief.action_required) == 1
    assert len(brief.schedule) == 1
    assert len(brief.tasks) == 1
    assert brief.ai_recommendation == "Review invoice first"
    assert brief.to_dict() == data


def test_get_llm_client_factory() -> None:
    """Test get_llm_client creates appropriate provider client."""
    client_gemini = get_llm_client("gemini")
    assert isinstance(client_gemini, GeminiClient)

    client_openai = get_llm_client("openai")
    assert isinstance(client_openai, OpenAIClient)

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm_client("anthropic")


@pytest.mark.asyncio
async def test_gemini_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GeminiClient raises RuntimeError when GEMINI_API_KEY is missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = GeminiClient(api_key=None)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        await client.generate([])


@pytest.mark.asyncio
async def test_gemini_successful_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful generation with GeminiClient."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")

    mock_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": """{
                                "headline": "Smooth morning ahead",
                                "missed": [],
                                "action_required": [
                                    {
                                        "title": "Deploy fix",
                                        "summary": "Critical",
                                        "source": "obsidian"
                                    }
                                ],
                                "schedule": [],
                                "tasks": [],
                                "ai_recommendation": "Deploy right away"
                            }"""
                        }
                    ]
                }
            }
        ]
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "models" in str(request.url)
        assert "key=test_gemini_key" in str(request.url)
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(mock_handler)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        client = GeminiClient()
        items = [
            BriefItem(
                source="obsidian",
                category="task",
                title="Deploy fix",
                body="Critical bug",
                priority=1,
            )
        ]
        result = await client.generate(items)
        assert result.headline == "Smooth morning ahead"
        assert len(result.action_required) == 1
        assert result.ai_recommendation == "Deploy right away"


@pytest.mark.asyncio
async def test_gemini_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test GeminiClient handles non-200 responses by raising RuntimeError."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")

    def mock_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(mock_handler)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        client = GeminiClient()
        with pytest.raises(RuntimeError, match="Gemini API request failed"):
            await client.generate([])


@pytest.mark.asyncio
async def test_openai_successful_generate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful generation with OpenAIClient."""
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")

    mock_response_data = {
        "choices": [
            {
                "message": {
                    "content": """{
                        "headline": "OpenAI Brief",
                        "missed": [],
                        "action_required": [],
                        "schedule": [],
                        "tasks": [{"title": "Check logs", "status": "open", "source": "obsidian"}],
                        "ai_recommendation": "Relax today"
                    }"""
                }
            }
        ]
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "chat/completions" in str(request.url)
        assert request.headers.get("Authorization") == "Bearer test_openai_key"
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(mock_handler)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        client = OpenAIClient()
        result = await client.generate([])
        assert result.headline == "OpenAI Brief"
        assert len(result.tasks) == 1
        assert result.ai_recommendation == "Relax today"


@pytest.mark.asyncio
async def test_test_llm_connection_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test test_llm_connection sending 'ping' to Gemini."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")

    mock_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "pong"}],
                    "role": "model",
                }
            }
        ]
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "generateContent" in str(request.url)
        content = json.loads(request.content.decode("utf-8"))
        assert content["contents"][0]["parts"][0]["text"] == "ping"
        return httpx.Response(200, json=mock_resp)

    transport = httpx.MockTransport(mock_handler)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        ok, msg, reply = await test_llm_connection("gemini")
        assert ok is True
        assert "Gemini API connected" in msg
        assert reply == "pong"


@pytest.mark.asyncio
async def test_test_llm_connection_gemini_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test test_llm_connection when GEMINI_API_KEY is missing."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    ok, msg, reply = await test_llm_connection("gemini")
    assert ok is False
    assert "GEMINI_API_KEY is missing" in msg
    assert reply is None

import os

import httpx

from the_daily_brief.config import get_config
from the_daily_brief.llm.base import BaseLLMClient
from the_daily_brief.llm.gemini import GeminiClient
from the_daily_brief.llm.openai import OpenAIClient


def get_llm_client(provider: str | None = None) -> BaseLLMClient:
    """Create and return an LLM client based on configuration or argument."""
    selected_provider = (provider or get_config().llm.provider or "gemini").lower()
    if selected_provider == "gemini":
        return GeminiClient()
    if selected_provider == "openai":
        return OpenAIClient()
    raise ValueError(f"Unsupported LLM provider: {selected_provider}")


async def test_llm_connection(provider: str | None = None) -> tuple[bool, str, str | None]:
    """Test connectivity and quota for the configured LLM provider with a 'ping' prompt."""
    config = get_config()
    selected_provider = (provider or config.llm.provider or "gemini").lower()
    if selected_provider == "gemini":
        key = (os.getenv("GEMINI_API_KEY") or "").strip()
        if not key:
            return False, "GEMINI_API_KEY is missing in .env", None
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{config.llm.model}:generateContent?key={key}"
        )
        payload = {"contents": [{"parts": [{"text": "ping"}]}]}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    reply = None
                    try:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                reply = parts[0].get("text", "").strip()
                    except Exception:
                        pass
                    return True, f"Gemini API connected ({config.llm.model}, key active)", reply
                err_detail = resp.text
                try:
                    err_json = resp.json()
                    err_detail = err_json.get("error", {}).get("message", resp.text)
                except Exception:
                    pass
                return False, f"Gemini API error ({resp.status_code}): {err_detail}", None
        except Exception as exc:
            return False, f"Network error contacting Gemini: {exc}", None

    if selected_provider == "openai":
        key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not key:
            return False, "OPENAI_API_KEY is missing in .env", None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                model_name = config.llm.model or "gpt-4o-mini"
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 50,
                    },
                )
                if resp.status_code == 200:
                    reply = None
                    try:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            reply = choices[0].get("message", {}).get("content", "").strip()
                    except Exception:
                        pass
                    return True, f"OpenAI API connected ({model_name})", reply
                return False, f"OpenAI error ({resp.status_code}): {resp.text}", None
        except Exception as exc:
            return False, f"Network error contacting OpenAI: {exc}", None

    return False, f"Unsupported provider: {selected_provider}", None


__all__ = [
    "BaseLLMClient",
    "GeminiClient",
    "OpenAIClient",
    "get_llm_client",
    "test_llm_connection",
]

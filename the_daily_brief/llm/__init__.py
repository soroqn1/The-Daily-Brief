"""LLM client subsystem."""

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


__all__ = ["BaseLLMClient", "GeminiClient", "OpenAIClient", "get_llm_client"]

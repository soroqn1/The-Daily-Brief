"""Gemini LLM client implementation."""

import json
import logging
import os
from typing import Any

import httpx

from the_daily_brief.config import get_config
from the_daily_brief.llm.base import BaseLLMClient
from the_daily_brief.models import BriefData, BriefItem

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model

    def _resolve_api_key(self) -> str:
        """Resolve Gemini API key from explicit arg or environment."""
        get_config()  # Ensure .env is loaded
        key = self._api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set in environment or configuration.")
        return key

    def _resolve_model(self) -> str:
        """Resolve model name from constructor or configuration."""
        if self._model:
            return self._model
        config = get_config()
        return config.llm.model or "gemini-3-flash-preview"

    def _build_prompt(self, items: list[BriefItem], language: str) -> str:
        """Build the structured prompt for the Gemini model."""
        formatted_items: list[dict[str, Any]] = []
        for item in items:
            formatted_items.append(
                {
                    "source": item.source,
                    "category": item.category,
                    "title": item.title,
                    "body": item.body,
                    "priority": item.priority,
                    "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                    "url": item.url,
                }
            )

        items_json = json.dumps(formatted_items, ensure_ascii=False, indent=2)

        return f"""You are the editor of "The Daily Brief", a morning newspaper.
Transform raw items gathered from connected sources into a briefing in {language}.

Raw Items Input:
{items_json}

Instructions:
1. Provide a punchy editorial headline summarizing the tone and load of the day.
2. Group items into the following 4 fixed sections in order:
   - "action_required": Urgent messages, unanswered emails requiring action,
     PRs, mentions, or invoices.
   - "missed": Emails, messages, and updates received overnight or while away.
   - "schedule": Time-based calendar meetings, events, or scheduled appointments.
   - "tasks": Open TODOs, goals, and project tasks (e.g. from Obsidian).
3. All sources (e.g. gmail, gmail_work, obsidian, calendar, slack, telegram)
   flow into these same sections. Every item MUST have an accurate "source"
   label (e.g. "gmail", "gmail · work", "obsidian", "calendar", "slack", "telegram").
4. Within each section, sort items by priority (most urgent first).
   For schedule items, sort by time. Mark urgent items with "urgent": true.
5. Provide a concise, actionable "ai_recommendation" guiding what to focus on first.
6. Preserve URLs where present so the user can click through.
7. If there are no items for a section, return an empty array [] for that section.
8. Do NOT fabricate or hallucinate events/emails that are not in the raw input.

Return ONLY a valid JSON object with this exact structure:
{{
  "headline": "String",
  "ai_recommendation": "String",
  "action_required": [
    {{
      "title": "String",
      "summary": "String",
      "source": "String",
      "urgent": true,
      "url": "String"
    }}
  ],
  "missed": [
    {{
      "title": "String",
      "summary": "String",
      "source": "String",
      "urgent": false,
      "url": "String"
    }}
  ],
  "schedule": [
    {{
      "time": "String",
      "title": "String",
      "summary": "String",
      "source": "String",
      "urgent": false,
      "url": "String"
    }}
  ],
  "tasks": [
    {{
      "title": "String",
      "summary": "String",
      "source": "String",
      "status": "open",
      "urgent": false,
      "url": "String"
    }}
  ]
}}"""

    async def generate(self, items: list[BriefItem]) -> BriefData:
        """Send raw brief items to Gemini API and receive structured BriefData."""
        api_key = self._resolve_api_key()
        model = self._resolve_model()
        config = get_config()
        language = config.brief_language or "en"

        prompt = self._build_prompt(items, language=language)
        url = f"{GEMINI_API_URL}/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        logger.info("Calling Gemini API with model %s (%d items)", model, len(items))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error(
                    "Gemini API call failed (status %d): %s",
                    response.status_code,
                    response.text,
                )
                raise RuntimeError(
                    f"Gemini API request failed with status {response.status_code}: {response.text}"
                )

            data = response.json()

        try:
            candidates = data.get("candidates", [])
            text_part = candidates[0]["content"]["parts"][0]["text"]
            parsed = json.loads(text_part)
            return BriefData.from_dict(parsed)
        except (KeyError, IndexError, json.JSONDecodeError) as err:
            logger.error("Failed to parse Gemini response payload: %s", data, exc_info=True)
            raise RuntimeError(f"Failed to parse structured response from Gemini: {err}") from err

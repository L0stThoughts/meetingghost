"""Action item extractor using Ollama local LLM."""
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Literal

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ActionItem:
    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "medium"


PROMPT_TEMPLATE = """You are a meeting assistant. Extract action items from the transcript below.

Return a JSON array where each element has:
- "description": string (the action item)
- "assignee": string or null (who is responsible)
- "due_date": string or null (any mentioned deadline)
- "priority": "high", "medium", or "low"

Speakers in this meeting: {speakers}

Transcript:
{transcript}

Return ONLY valid JSON array, no other text."""


class ActionExtractor:
    def __init__(self, ollama_url: str, model: str = "phi3:mini") -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model

    async def extract(self, transcript: str, speakers: List[str]) -> List[ActionItem]:
        if not transcript.strip():
            return []

        prompt = PROMPT_TEMPLATE.format(
            speakers=", ".join(speakers) if speakers else "Unknown",
            transcript=transcript[:4000],
        )

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                body = resp.json()
                raw = body.get("response", "")
        except Exception as exc:
            logger.error("Ollama request failed: %s", exc)
            return []

        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: str) -> List[ActionItem]:
        try:
            start = raw.find("[")
            end = raw.rfind("]")
            if start == -1 or end == -1:
                return []
            items_data = json.loads(raw[start:end + 1])
            items: List[ActionItem] = []
            for item in items_data:
                if not isinstance(item, dict) or "description" not in item:
                    continue
                priority = item.get("priority", "medium")
                if priority not in ("high", "medium", "low"):
                    priority = "medium"
                items.append(ActionItem(
                    description=item["description"],
                    assignee=item.get("assignee"),
                    due_date=item.get("due_date"),
                    priority=priority,
                ))
            return items
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse action items: %s", exc)
            return []

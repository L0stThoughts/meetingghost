"""Meeting summarizer using Ollama local LLM."""
import json
import logging
from dataclasses import dataclass, field
from typing import List

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MeetingSummary:
    title: str
    one_liner: str
    key_points: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)


PROMPT_TEMPLATE = """You are a meeting assistant. Summarize the following meeting transcript.

Meeting duration: {duration} minutes.

Return a JSON object with:
- "title": a short descriptive title for this meeting
- "one_liner": a single sentence summary
- "key_points": array of key discussion points (strings)
- "decisions": array of decisions made (strings)

Transcript:
{transcript}

Return ONLY valid JSON, no other text."""


class MeetingSummarizer:
    def __init__(self, ollama_url: str, model: str = "phi3:mini") -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model

    async def summarize(self, transcript: str, duration_seconds: int) -> MeetingSummary:
        if not transcript.strip():
            return MeetingSummary(title="Empty Meeting", one_liner="No content recorded.")

        duration_min = max(1, duration_seconds // 60)
        prompt = PROMPT_TEMPLATE.format(
            duration=duration_min,
            transcript=transcript[:4000],
        )

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                raw = resp.json().get("response", "")
        except Exception as exc:
            logger.error("Ollama summarize failed: %s", exc)
            return MeetingSummary(title="Meeting", one_liner="Summary unavailable.")

        return self._parse_response(raw)

    @staticmethod
    def _parse_response(raw: str) -> MeetingSummary:
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("No JSON object found")
            data = json.loads(raw[start:end + 1])
            return MeetingSummary(
                title=data.get("title", "Meeting"),
                one_liner=data.get("one_liner", ""),
                key_points=data.get("key_points", []),
                decisions=data.get("decisions", []),
            )
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("Failed to parse summary: %s", exc)
            return MeetingSummary(title="Meeting", one_liner="Summary could not be parsed.")

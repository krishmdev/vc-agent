"""Deep-research providers.

Both providers go through the same task/status flow in main.py: the task is created as
"queued", moves to "running" while progress notes arrive, and ends "completed" or "failed".
"""

import asyncio
import time
from typing import Any, Callable, Protocol

from google import genai
from google.genai import types

import settings
from prompts import FAST_CHAT_INSTRUCTION, build_fast_chat_prompt

# stage ("queued" | "running"), optional human-readable note
ProgressFn = Callable[[str, str | None], None]


class ResearchError(RuntimeError):
    pass


class ResearchProvider(Protocol):
    name: str

    async def deep_research(self, prompt: str, *, context: str, on_progress: ProgressFn) -> str: ...

    async def follow_up(
        self, history: list[dict[str, str]], user_message: str, context: str
    ) -> str: ...


def progress_notes(steps: list[Any] | None) -> list[str]:
    """Readable notes from deep-research steps: thought summaries and search queries."""
    notes: list[str] = []
    for step in steps or []:
        kind = getattr(step, "type", None)
        if kind == "thought":
            for item in getattr(step, "summary", None) or []:
                text = (getattr(item, "text", None) or "").strip()
                if text:
                    notes.append(text)
        elif kind == "google_search_call":
            args = getattr(step, "arguments", None)
            queries = getattr(args, "queries", None) or []
            if queries:
                notes.append("Searching: " + "; ".join(str(q) for q in queries[:3]))
    return notes


class GeminiResearchProvider:
    """First turn: the Gemini Deep Research agent. Follow-ups: Gemini Flash with Search grounding."""

    name = "gemini"

    def __init__(
        self,
        api_key: str,
        *,
        agent: str = settings.DEEP_RESEARCH_AGENT,
        chat_model: str = settings.CHAT_MODEL,
        poll_interval: float = 10.0,
        timeout_s: float = 30 * 60,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self.agent = agent
        self.chat_model = chat_model
        self.poll_interval = poll_interval
        self.timeout_s = timeout_s

    async def deep_research(self, prompt: str, *, context: str, on_progress: ProgressFn) -> str:
        interaction = await self._client.aio.interactions.create(
            input=prompt,
            agent=self.agent,
            background=True,
            agent_config={"type": "deep-research", "thinking_summaries": "auto"},
        )
        interaction_id = interaction.id
        on_progress("running", f"Deep research started ({self.agent})")
        started = time.monotonic()
        seen = 0
        while True:
            interaction = await self._client.aio.interactions.get(interaction_id)
            notes = progress_notes(interaction.steps)
            for note in notes[seen:]:
                on_progress("running", note)
            seen = len(notes)

            if interaction.status == "completed":
                text = interaction.output_text
                if not text:
                    raise ResearchError("Deep research finished without a report")
                return text
            if interaction.status in {"failed", "cancelled", "incomplete", "budget_exceeded"}:
                raise ResearchError(f"Deep research {interaction.status}: {interaction.errors}")
            if time.monotonic() - started > self.timeout_s:
                raise ResearchError("Deep research timed out")
            await asyncio.sleep(self.poll_interval)

    async def follow_up(self, history: list[dict[str, str]], user_message: str, context: str) -> str:
        contents = [
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part.from_text(text=msg["content"])],
            )
            for msg in history
        ]
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=build_fast_chat_prompt(user_message, context))],
            )
        )
        response = await self._client.aio.models.generate_content(
            model=self.chat_model,
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=FAST_CHAT_INSTRUCTION,
            ),
        )
        if not response.text:
            raise ResearchError("Empty follow-up response")
        return response.text


class MissingKeyResearchProvider:
    name = "unconfigured"

    async def deep_research(self, prompt: str, *, context: str, on_progress: ProgressFn) -> str:
        raise ResearchError("API Key missing")

    async def follow_up(self, history, user_message, context) -> str:
        raise ResearchError("API Key missing")


def make_research_provider() -> ResearchProvider:
    if settings.OFFLINE:
        from fixture_research import FixtureResearchProvider

        return FixtureResearchProvider(settings.FIXTURE_DIR)
    key = settings.gemini_api_key()
    if not key:
        return MissingKeyResearchProvider()
    return GeminiResearchProvider(key)

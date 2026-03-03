"""Resource-drawer guides grounded in the Sequoia knowledge base.

The drawer asks for a tactical guide on one dashboard question. We retrieve passages from the
knowledge base, number them, and have the writer cite them as [n]. Live mode writes with Gemini;
offline mode assembles the guide from the retrieved sentences with no language model.
"""

import re
from typing import Protocol

from google import genai
from google.genai import types

import settings
from kb_client import Passage
from prompts import build_guide_prompt
from textutil import best_sentences

PASSAGE_CHARS = 1500


def citations_for(passages: list[Passage]) -> list[dict]:
    return [
        {
            "n": i,
            "source": p.source,
            "type": p.type,
            "url": p.url,
            "snippet": _snippet(p.text),
        }
        for i, p in enumerate(passages, start=1)
    ]


def _body(text: str) -> str:
    # Chunks are stored with a "[From: <source>]" header line; readers don't need it.
    if text.startswith("[From:"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    return text.strip()


_MARKDOWN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)|[*_`#>]+|\[\d+\]")
_HEADING = re.compile(r"^\s*#{1,6}\s.*$", re.M)


def _prose(text: str) -> str:
    """Passage body as plain prose: heading lines dropped (they have no end punctuation and would
    run into the next sentence), link text kept, markdown marks and URLs removed."""
    return _MARKDOWN.sub(lambda m: m.group(1) or "", _HEADING.sub("", _body(text)))


def _snippet(text: str, limit: int = 220) -> str:
    body = " ".join(_prose(text).split())
    return body if len(body) <= limit else body[: limit - 1].rsplit(" ", 1)[0] + "…"


def sources_block(passages: list[Passage]) -> str:
    return "\n\n".join(
        f"[{i}] {p.source} ({p.type})\n{_body(p.text)[:PASSAGE_CHARS]}"
        for i, p in enumerate(passages, start=1)
    )


class GuideWriter(Protocol):
    name: str

    async def write_guide(self, question: str, passages: list[Passage]) -> str: ...

    async def answer(
        self, message: str, history: list[dict[str, str]], article: str, passages: list[Passage]
    ) -> str: ...


class GeminiGuideWriter:
    name = "gemini"

    def __init__(self, api_key: str, model: str = settings.CHAT_MODEL) -> None:
        self._client = genai.Client(api_key=api_key)
        self.model = model

    async def write_guide(self, question: str, passages: list[Passage]) -> str:
        # With the Google Search tool attached, Gemini drops the [n] citations to our excerpts
        # (checked 2026-03-01), so Search is only used when the knowledge base returned nothing.
        tools = None if passages else [types.Tool(google_search=types.GoogleSearch())]
        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=build_guide_prompt(question, sources_block(passages)),
            config=types.GenerateContentConfig(tools=tools),
        )
        if not response.text:
            raise RuntimeError("Failed to generate content")
        return response.text

    async def answer(self, message, history, article, passages) -> str:
        contents = [
            types.Content(
                role="user" if msg["role"] == "user" else "model",
                parts=[types.Part.from_text(text=msg["content"])],
            )
            for msg in history
        ]
        prompt = f"""
        You are a helpful assistant answering questions about a specific article.

        ARTICLE CONTEXT:
        {article}

        RELATED SEQUOIA KNOWLEDGE BASE EXCERPTS:
        {sources_block(passages) or "(none found)"}

        USER QUESTION:
        {message}

        INSTRUCTIONS:
        - Answer strictly based on the provided article context, the excerpts, and your general startup knowledge.
        - When you use an excerpt, cite its number in square brackets, e.g. [1].
        - Be concise and helpful.
        """
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
        response = await self._client.aio.models.generate_content(model=self.model, contents=contents)
        return response.text or ""


class ExtractiveGuideWriter:
    """Offline writer: picks the retrieved sentences that overlap the question most."""

    name = "extractive"

    async def write_guide(self, question: str, passages: list[Passage]) -> str:
        if not passages:
            return (
                "**Core Principle**\n\nThe offline knowledge base returned nothing for this "
                "question. Try rephrasing it with a company or founder name."
            )
        picks = [(i, best_sentences(question, _prose(p.text), k=2)) for i, p in enumerate(passages, 1)]
        lead_n, lead = next(((i, s) for i, s in picks if s), (1, []))
        lines = ["**Core Principle**", ""]
        lead_source = _short(passages[lead_n - 1].source)
        lines.append(f'From "{lead_source}": {lead[0]} [{lead_n}]' if lead else f"{_snippet(passages[0].text)} [1]")
        bullets = []
        for i, sents in picks:
            if not sents:
                continue
            quote = sents[1] if i == lead_n and len(sents) > 1 else sents[0]
            if lead and quote == lead[0]:
                continue
            bullets.append(f"- **{_short(passages[i - 1].source)}:** \"{quote}\" [{i}]")
        if bullets:
            lines += ["", "**What founders in the knowledge base said**", "", *bullets]
        lines += [
            "",
            "**Key Signal**",
            "",
            "Look for the pattern that repeats across these stories, then test it against your "
            "own customers before building more.",
            "",
            "_Offline mode: assembled from retrieved Sequoia passages without a language model._",
        ]
        return "\n".join(lines)

    async def answer(self, message, history, article, passages) -> str:
        found = []
        for i, p in enumerate(passages, 1):
            for s in best_sentences(message, _prose(p.text), k=1):
                found.append(f"{s} [{i}]")
        if not found:
            return "I couldn't find anything in the offline knowledge base for that question."
        return " ".join(found[:3]) + "\n\n_Offline mode: sentences quoted from the knowledge base._"


def _short(source: str, limit: int = 60) -> str:
    return source if len(source) <= limit else source[: limit - 1].rsplit(" ", 1)[0] + "…"


def make_guide_writer() -> GuideWriter | None:
    if settings.OFFLINE:
        return ExtractiveGuideWriter()
    key = settings.gemini_api_key()
    return GeminiGuideWriter(key) if key else None

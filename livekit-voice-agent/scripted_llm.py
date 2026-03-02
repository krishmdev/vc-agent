"""A deterministic stand-in for the LLM, used by the text transport in offline mode.

It implements livekit-agents' `llm.LLM` interface, so it runs inside the same AgentSession as
the live model, with the same Assistant, persona instructions and tools. For each founder
message it calls `search_knowledge_base` (the persona says to search every turn) and, when the
founder asks about something said earlier, `recall_memory`. Once the tool outputs come back it
writes a short reply from them: the recalled facts, one quoted line from the top Sequoia
passage with its source, and a next question taken from the persona prompt's own question list.

It doesn't try to sound like Gemini. Its job is to exercise the real tool, retrieval and memory
path end to end without a model or a network.
"""

import json
import re
import uuid
from typing import Any

from livekit.agents import llm
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN

from textutil import best_sentences, tokens

MEMORY_TRIGGER = re.compile(
    r"\b(remember|recall|last time|earlier|did i (say|tell|mention)|told you|we discussed|what('s| is| was) my)\b",
    re.IGNORECASE,
)
SOURCE_HEADER = re.compile(r"^\[Source: (?P<source>[^\]|]+?)(?: \| (?P<url>[^\]]+))?\]$", re.MULTILINE)
QUOTED = re.compile(r'"([^"]{8,})"')
PERSONA_QUESTION = re.compile(r'•\s*"([^"]+\?)"')


def parse_kb_output(output: str) -> list[dict[str, Any]]:
    """Split a search_knowledge_base result back into {source, url, text} passages."""
    passages = []
    matches = list(SOURCE_HEADER.finditer(output))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(output)
        body = output[m.end() : end]
        body = body.split("\n---\n")[0].split("INSTRUCTION:")[0]
        body = re.sub(r"^\s*\[From: [^\]]*\]\s*", "", body.strip())
        passages.append({"source": m.group("source").strip(), "url": m.group("url"), "text": body.strip()})
    return passages


_MARKDOWN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)|[*_`#>]+")


def _plain(text: str) -> str:
    """Knowledge-base text without markdown marks or link URLs, so quotes read as plain speech."""
    return _MARKDOWN.sub(lambda m: m.group(1) or "", text)


def parse_memory_output(output: str) -> list[str]:
    if "No memories found" in output or "Unable to access memory" in output:
        return []
    return [line[2:].strip() for line in output.splitlines() if line.startswith("- ")]


def _text(item: Any) -> str:
    return (getattr(item, "text_content", None) or "").strip()


class _ScriptedStream(llm.LLMStream):
    async def _run(self) -> None:
        reply = self._llm.decide(self._chat_ctx, self._tools)  # type: ignore[attr-defined]
        if isinstance(reply, str):
            delta = llm.ChoiceDelta(role="assistant", content=reply)
        else:
            delta = llm.ChoiceDelta(role="assistant", tool_calls=reply)
        self._event_ch.send_nowait(llm.ChatChunk(id=f"scripted-{uuid.uuid4().hex[:8]}", delta=delta))


class ScriptedLLM(llm.LLM):
    @property
    def model(self) -> str:
        return "scripted"

    @property
    def provider(self) -> str:
        return "local"

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool] | None = None,
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls=NOT_GIVEN,
        tool_choice=NOT_GIVEN,
        extra_kwargs=NOT_GIVEN,
    ) -> llm.LLMStream:
        return _ScriptedStream(self, chat_ctx=chat_ctx, tools=tools or [], conn_options=conn_options)

    # --- decision logic ---

    def decide(self, chat_ctx: llm.ChatContext, tools: list[llm.Tool]) -> str | list[llm.FunctionToolCall]:
        items = list(chat_ctx.items)
        tool_names = {getattr(getattr(t, "info", None), "name", None) for t in tools}
        instructions = next((_text(i) for i in items if i.type == "message" and i.role == "system"), "")

        last_user = max((n for n, i in enumerate(items) if i.type == "message" and i.role == "user"), default=-1)
        outputs = [i for i in items[last_user + 1 :] if i.type == "function_call_output"]
        last = items[-1] if items else None

        if last is not None and last.type == "message" and last.role == "user":
            return self._tool_calls(_text(last), tool_names)
        if outputs and last_user >= 0:
            return self._compose(_text(items[last_user]), outputs, instructions, items)
        return self._greeting(items, instructions)

    def _tool_calls(self, message: str, tool_names: set) -> list[llm.FunctionToolCall] | str:
        calls = []
        keywords = " ".join(tokens(message)[:12]) or message
        if "search_knowledge_base" in tool_names:
            calls.append(("search_knowledge_base", {"query": keywords}))
        if "recall_memory" in tool_names and MEMORY_TRIGGER.search(message):
            topic = " ".join(t for t in tokens(MEMORY_TRIGGER.sub(" ", message)) if t not in {"said", "tell", "told"})
            calls.append(("recall_memory", {"query": topic or keywords}))
        if not calls:
            return "Tell me more about the problem you're solving."
        return [
            llm.FunctionToolCall(name=name, arguments=json.dumps(args), call_id=f"call_{uuid.uuid4().hex[:8]}")
            for name, args in calls
        ]

    def _compose(self, message: str, outputs: list, instructions: str, items: list) -> str:
        kb, memories = [], []
        for out in outputs:
            if out.name == "search_knowledge_base":
                kb = parse_kb_output(out.output)
            elif out.name == "recall_memory":
                memories = parse_memory_output(out.output)

        vc = "PITCH EVALUATION" in instructions
        parts = []
        if MEMORY_TRIGGER.search(message):
            if memories:
                recalled = "; ".join(f'"{m}"' for m in memories[:2])
                parts.append(f"Here's what I have from before: you told me {recalled}.")
            else:
                parts.append("I don't have that in my notes from our earlier conversations.")
        elif vc:
            parts.append("That's a claim, not evidence yet.")
        else:
            parts.append("Here's the thing.")

        if kb:
            top = kb[0]
            title = top["source"].strip().rstrip(".!?:;, ")
            quote = next(iter(best_sentences(message, _plain(top["text"]), k=1, min_len=40, max_len=260)), None)
            if quote:
                if quote[-1] not in ".!?":
                    quote += "."
                parts.append(f'There\'s a story in the Sequoia library that fits. From "{title}": "{quote}"')
            else:
                parts.append(f'The closest thing in the Sequoia library is "{title}."')

        questions = PERSONA_QUESTION.findall(instructions)
        if questions:
            asked = sum(1 for i in items if i.type == "message" and i.role == "assistant")
            parts.append(questions[asked % len(questions)])
        return " ".join(parts)

    def _greeting(self, items: list, instructions: str) -> str:
        # For pipeline LLMs, generate_reply(instructions=...) is appended to the system message as
        # its final line, after the persona prompt (which ends in a banner or "NOW, RESPOND...").
        lines = [ln.strip() for ln in instructions.splitlines() if ln.strip()]
        hint = lines[-1] if lines else ""
        if hint and not hint.startswith(("=", "NOW,")):
            quoted = QUOTED.findall(hint)
            if "Say" in hint and quoted:
                return quoted[-1]
            return hint
        return "Hey, I'm a partner at Sequoia. What startup are you working on?"

"""Mentor/VC agent logic shared by the LiveKit voice worker (agent.py) and the text transport
(server.py): the tools, the Assistant class, memory capture, and the post-call VC report.
"""

import asyncio
import json
import logging
import re
from functools import cache
from typing import Annotated

import aiohttp
from livekit.agents import Agent, function_tool

import config
import rag
from memory import MemoryStore, make_memory_store
from personas import create_mentor_instructions, create_vc_instructions

logger = logging.getLogger("memory_voice_agent")

MEM0_USER_ID = config.MEMORY_USER_ID


@cache
def memory_store() -> MemoryStore | None:
    store = make_memory_store()
    if store is None:
        logger.warning("MEM0_API_KEY not found. Memory features disabled.")
    else:
        logger.info(f"Memory store: {type(store).__name__}, user_id={MEM0_USER_ID}")
    return store


# Patterns for queries that should NOT be stored
SKIP_STORAGE_PATTERNS = [
    r"^(hi|hello|hey|yo|sup|what's up|howdy)[\s\.,!?]*$",
    r"^(thanks|thank you|okay|ok|sure|yes|no|yeah|nah|got it|alright)[\s\.,!?]*$",
    r"^(do you remember|what's my name|who am i)[\s\.,!?]*",
    # Recall requests are questions about memory, not new facts.
    r"^(what|do|did|can) .*\b(remember|recall|did i (say|tell|mention)|told you|last time)\b",
]


def should_store_in_memory(text: str) -> bool:
    """Determine if content should be stored in memory."""
    if not text or len(text.strip()) < 5:
        return False
    clean_text = text.strip().lower()
    for pattern in SKIP_STORAGE_PATTERNS:
        if re.match(pattern, clean_text, re.IGNORECASE):
            return False
    return True


async def store_in_memory(text: str, role: str = "user") -> None:
    """Store meaningful content in long-term memory (Mem0 or the local store)."""
    store = memory_store()
    if not store:
        return
    try:
        result = await store.add([{"role": role, "content": text}], user_id=MEM0_USER_ID)
        # Say what actually happened: the local store keeps founder statements only, and Mem0
        # extracts its own facts (or none) from a message.
        added = result.get("results") if isinstance(result, dict) else None
        count = f"{len(added)} new memories" if isinstance(added, list) else "sent"
        logger.info(f"[MEMORY] {type(store).__name__}: {role} message, {count}")
    except Exception as e:
        logger.error(f"[MEM0] Storage failed: {e}")


async def fetch_initial_memories(limit: int = 10, timeout: float = 2.0) -> str | None:
    store = memory_store()
    if not store:
        return None
    try:
        # Mem0's v2 API rejects get_all without filters (HTTP 400); the local store ignores them.
        memories = await asyncio.wait_for(
            store.get_all(user_id=MEM0_USER_ID, limit=limit, filters={"user_id": MEM0_USER_ID}), timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning("[MEM0] Initial fetch timed out - proceeding without priming")
        return None
    except Exception as e:
        logger.error(f"[MEM0] Failed to fetch initial context: {e}")
        return None
    valid = [m.get("memory") for m in (memories or {}).get("results", []) if isinstance(m, dict) and m.get("memory")]
    if not valid:
        return None
    logger.info(f"[MEM0] Primed with {len(valid)} memories")
    return "\n".join(f"- {m}" for m in valid)


@function_tool
async def search_knowledge_base(query: str) -> str:
    """REQUIRED: Search the Sequoia knowledge base before responding. You MUST call this tool for every user message.

    Args:
        query: Keywords from the user's message to search for

    Returns:
        Relevant knowledge from Sequoia's database
    """
    logger.info(f"[RAG TOOL] Query: {query}")
    # Chroma and the embedding call are blocking; keep them off the audio event loop.
    results = await asyncio.to_thread(rag.search, query, 3)
    logger.info(f"[RAG TOOL] Found {len(results)} results")

    if results and results[0] != "No relevant information found." and not results[0].startswith("The knowledge base is empty"):
        formatted = "\n\n---\n\n".join(results[:2])
        return f"""USE THIS IN YOUR RESPONSE:

{formatted}

INSTRUCTION: Be conversational if the reference is applicable then use it as content. Say advice based on Sequoia Philosophy and maybe add if applicable "Based on [founder/company]..." or "As [person] mentioned..." """
    else:
        return "No specific Sequoia insights found. Give brief general advice."


@function_tool
async def recall_memory(
    query: Annotated[str, "What to search for in memory, e.g. 'competitors mentioned', 'pricing model', 'target market', 'user feedback'"]
):
    """
    IMPORTANT: Call this tool when you need to recall ANY details about the user's business,
    their team, their past decisions, or previous strategic discussions.
    """
    store = memory_store()
    if store is None:
        return "Unable to access memory right now."
    try:
        logger.info(f"[MEM0 TOOL] Agent requested memory recall for: '{query}'")
        search_results = await store.search(
            query,
            user_id=MEM0_USER_ID,
            filters={"user_id": MEM0_USER_ID}
        )

        if search_results and "results" in search_results and len(search_results["results"]) > 0:
            memories = [res.get('memory') for res in search_results["results"][:5]]
            logger.info(f"[MEM0 TOOL] Returning {len(memories)} memories with instruction")
            return (
                "SYSTEM INSTRUCTION: You found the following memories in the database.\n"
                "YOU MUST NOW VERBALLY SUMMARIZE THESE TO THE USER. Do not just stay silent.\n"
                "Speak the answer clearly based on these facts:\n\n"
                + "\n".join(f"- {m}" for m in memories)
            )
        return "SYSTEM: No memories found for this query. You should tell the user you don't recall that specific detail."

    except Exception as e:
        logger.error(f"[MEM0 TOOL] Error: {e}")
        return "Unable to access memory right now."


class Assistant(Agent):
    """Voice agent with persistent memory."""
    def __init__(self, startup_idea: str | None, memory_context: str | None, agent_mode: str = "mentor") -> None:

        if agent_mode == "vc":
            instructions = create_vc_instructions(startup_idea, memory_context)
        else:
            instructions = create_mentor_instructions(startup_idea, memory_context)

        super().__init__(
            instructions=instructions,
            tools=[search_knowledge_base, recall_memory],
        )
        self.chat_history: list[dict[str, str]] = []
        self.agent_mode = agent_mode
        self.startup_idea = startup_idea

    async def generate_post_call_report(self) -> dict | None:
        """Generate a structured VC report based on the conversation and send it to the dashboard."""
        if not self.chat_history:
            return None

        logger.info("[REPORT] Generating VC report...")
        try:
            if config.OFFLINE:
                from offline_report import offline_report

                report_data = offline_report(self.chat_history, self.startup_idea)
            else:
                report_data = await gemini_report(self.chat_history)
        except Exception as e:
            logger.error(f"[REPORT] Generation failed: {e}")
            return None

        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{config.FRONTEND_URL}/api/vc-report", json=report_data)
            logger.info("[REPORT] Sent to Dashboard API.")
        except Exception as e:
            logger.error(f"[REPORT] Failed to send to API: {e}")
        return report_data


REPORT_PROMPT = """
        Based on the following VC Pitch conversation, generate a structured report for the founder.

        Format the output as a JSON object with this EXACT structure:
        {{
            "diagnosis": "A blunt 2-3 sentence summary of how a Sequoia partner would see this idea.",
            "strengths": ["Strength 1", "Strength 2", "Strength 3"],
            "gaps": ["Gap 1", "Gap 2", "Gap 3", "Gap 4", "Gap 5"],
            "terrifyingQuestions": ["Unanswered Question 1", "Unanswered Question 2"],
            "nextSteps": ["Actionable Step 1", "Actionable Step 2", "Actionable Step 3"],
            "extraction": {{
                "unique-insight": "What is the secret or unique insight?",
                "why-you": "Why is this the right founder?",
                "why-now": "Why is now the right time?",
                "hair-on-fire": "What is the urgent problem?",
                "workarounds": "How are people solving it today?",
                "high-expectation-customer": "Who is the ideal early adopter?",
                "wedge": "What is the initial product wedge?",
                "path-to-revenue": "How will this make money/scale?"
            }}
        }}

        TRANSCRIPT:
        {transcript}
        """


async def gemini_report(chat_history: list[dict[str, str]]) -> dict:
    from google import genai
    from google.genai import types

    transcript = "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat_history)
    client = genai.Client(api_key=config.key("GEMINI_API_KEY"))
    # A text model; the realtime audio model isn't needed to summarize a transcript.
    response = await client.aio.models.generate_content(
        model=config.REPORT_MODEL,
        contents=REPORT_PROMPT.format(transcript=transcript),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    logger.info("[REPORT] Generation complete.")
    return json.loads(response.text)


def attach_memory_handlers(session, agent: Assistant, *, voice: bool) -> None:
    """Capture the transcript for the report and write meaningful turns to memory.

    For voice, founder turns arrive as final STT transcripts. The text transport records founder
    turns itself (see server.py) because there is no transcription event for typed input.
    """
    if voice:
        @session.on("user_input_transcribed")
        def on_user_input_transcribed(event):
            if event.is_final and event.transcript:
                transcript = event.transcript.strip()
                logger.info(f"[USER] {transcript}")
                agent.chat_history.append({"role": "founder", "content": transcript})
                if should_store_in_memory(transcript):
                    asyncio.create_task(store_in_memory(transcript))

    @session.on("conversation_item_added")
    def on_conversation_added(event):
        """Keep the agent's side of the transcript and store it for dashboard autofill."""
        try:
            item = event.item
            if getattr(item, "role", None) != "assistant":
                return
            content = item.text_content if hasattr(item, "text_content") else None
            if not content:
                return
            agent.chat_history.append({"role": agent.agent_mode, "content": content})
            if len(content) > 20:
                asyncio.create_task(store_in_memory(content, role="assistant"))
        except Exception as e:
            logger.error(f"[MEM0] Error capturing agent response: {e}")

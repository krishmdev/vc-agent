# Load environment variables FIRST (before imports that need them)
from dotenv import load_dotenv
from pathlib import Path
import os
import json
import ssl
import logging
import asyncio
import re
from typing import Annotated

from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent, room_io, function_tool
from livekit.plugins import openai, silero
from openai.types import realtime
from mem0 import AsyncMemoryClient
import rag

# Load env files
env_path_local = Path(__file__).resolve().parent / ".env.local"
env_path_parent = Path(__file__).resolve().parent.parent / ".env.local"
load_dotenv(env_path_local)
load_dotenv(env_path_parent)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("memory_voice_agent")

# Configure SSL context for macOS
try:
    import certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())
except (PermissionError, ImportError):
    ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True
ssl_context.verify_mode = ssl.CERT_REQUIRED

# Global Mem0 Client & ID (Configured for reliable dev testing)
MEM0_USER_ID = "sequoia-mentor-agent" 
mem0_api_key = os.getenv("MEM0_API_KEY")

if mem0_api_key:
    mem0_client = AsyncMemoryClient(api_key=mem0_api_key)
    logger.info(f"Mem0 client initialized. Using user_id: {MEM0_USER_ID}")
else:
    mem0_client = None
    logger.warning("MEM0_API_KEY not found. Memory features disabled.")

# Patterns for queries that should NOT be stored
SKIP_STORAGE_PATTERNS = [
    r"^(hi|hello|hey|yo|sup|what's up|howdy)[\s\.,!?]*$",
    r"^(thanks|thank you|okay|ok|sure|yes|no|yeah|nah|got it|alright)[\s\.,!?]*$",
    r"^(do you remember|what's my name|who am i)[\s\.,!?]*",
]

def should_store_in_memory(text: str) -> bool:
    """Determine if content should be stored in memory."""
    if not text or len(text.strip()) < 15:
        return False
    clean_text = text.strip().lower()
    for pattern in SKIP_STORAGE_PATTERNS:
        if re.match(pattern, clean_text, re.IGNORECASE):
            return False
    return True

@function_tool
async def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information."""
    results = rag.search(query, top_k=10)
    return "\n\n---\n\n".join(results)

@function_tool
async def recall_memory(
    query: Annotated[str, "What to search for in memory, e.g. 'competitors mentioned', 'pricing model', 'target market', 'user feedback'"]
):
    """
    IMPORTANT: Call this tool when you need to recall ANY details about the user's business, 
    their team, their past decisions, or previous strategic discussions.
    """
    try:
        logger.info(f"[MEM0 TOOL] Agent requested memory recall for: '{query}'")
        
        search_results = await mem0_client.search(
            query, 
            user_id=MEM0_USER_ID,
            filters={"user_id": MEM0_USER_ID}
        )
        
        if search_results and "results" in search_results and len(search_results["results"]) > 0:
            memories = [res.get('memory') for res in search_results["results"][:5]]
            
            # Format as imperative instruction
            result = (
                "SYSTEM INSTRUCTION: You found the following memories in the database.\n"
                "YOU MUST NOW VERBALLY SUMMARIZE THESE TO THE USER. Do not just stay silent.\n"
                "Speak the answer clearly based on these facts:\n\n"
                + "\n".join(f"- {m}" for m in memories)
            )
            logger.info(f"[MEM0 TOOL] Returning {len(memories)} memories with instruction")
            return result
        else:
            return "SYSTEM: No memories found for this query. You should tell the user you don't recall that specific detail."
            
    except Exception as e:
        logger.error(f"[MEM0 TOOL] Error: {e}")
        return "Unable to access memory right now."

def create_mentor_instructions(startup_idea: str | None = None, memory_context: str | None = None) -> str:
    """Create mentor instructions with dynamic memory context."""
    idea_context = ""
    if startup_idea:
        idea_context = f"""
CURRENT PITCH:
The founder is building: "{startup_idea}"
Drill down on this - don't accept vague descriptions.
"""

    return f"""SYSTEM PRIORITY #1: MEMORY TOOL USAGE
You possess a long-term memory via the `recall_memory` tool. 
If the user asks ANY question about the past, their identity, or your previous discussions, you MUST use `recall_memory` BEFORE responding.

Triggers for `recall_memory`:
1. "Do you remember me?" / "What is my name?"
2. "What did we talk about last time?"
3. "Do you remember my startup idea?"
4. "What did I say about [topic]?"

DO NOT hallucinate or guess. If they ask "Do you remember X?", call `recall_memory(query="X")` immediately.

=== MEMORIES ALREADY RETRIEVED (Use these first) ===
{memory_context if memory_context else "No initial memories found."}
===================================================

=== CURRENT CONTEXT ===
{idea_context if idea_context else "No specific startup idea provided yet."}
=======================

You are a Senior Partner at Sequoia Capital. Direct, skeptical, no-nonsense.

CORE PHILOSOPHY:
"Vague ideas die." Zero tolerance for ambiguity.

INTERROGATION TOOLKIT:
1. **Desperation Check:** "Who exactly is *desperate* for this right now?"
2. **Why Now:** "Why is *this exact moment* the only time this can work?"
3. **Incumbent Threat:** "If this works, Google copies you in a weekend. What's your defense?"
4. **Unit Economics:** "Explain the math. Cost per customer vs revenue per customer."
5. **Pre-Mortem:** "2 years from now, your company is dead. What decision killed it?"

STYLE:
- Short, punchy sentences
- Never accept broad categories ("gamers" → "Mobile or PC? Casual or Hardcore?")
- Drill deeper on every answer
- Cite Sequoia portfolio examples (Airbnb, Stripe, WhatsApp)
"""

class Assistant(Agent):
    """Voice agent with persistent memory."""
    def __init__(self, startup_idea: str | None, memory_context: str | None) -> None:
        super().__init__(
            instructions=create_mentor_instructions(startup_idea, memory_context),
            tools=[search_knowledge_base, recall_memory], 
        )

server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()
    participant = await ctx.wait_for_participant()
    
    # Extract startup idea from participant metadata
    startup_idea = None
    if participant.metadata:
        try:
            metadata = json.loads(participant.metadata)
            startup_idea = metadata.get("startupIdea")
        except json.JSONDecodeError:
            pass

    # --- INITIAL FETCH ---
    initial_memory_context = None
    if mem0_client:
        try:
            logger.info(f"[MEM0] Fetching initial context (timeout=2s)...")
            async def fetch_memories():
                return await mem0_client.get_all(user_id=MEM0_USER_ID, limit=10)
            
            # 2s timeout
            memories = await asyncio.wait_for(fetch_memories(), timeout=2.0)
            
            if memories and "results" in memories:
                valid_mems = [m.get("memory") for m in memories["results"] if isinstance(m, dict) and m.get("memory")]
                if valid_mems:
                    initial_memory_context = "\n".join(f"- {m}" for m in valid_mems)
                    logger.info(f"[MEM0] Primed with {len(valid_mems)} memories")
        except asyncio.TimeoutError:
            logger.warning(f"[MEM0] Initial fetch timed out - proceeding without priming")
        except Exception as e:
            logger.error(f"[MEM0] Failed to fetch initial context: {e}")

    # --- SESSION SETUP ---
    realtime_model = openai.realtime.RealtimeModel(
        model="gpt-4o-mini-realtime-preview",
        voice="alloy",
        modalities=["audio", "text"],
        input_audio_transcription=realtime.AudioTranscription(model="gpt-4o-mini-transcribe"),
        turn_detection=realtime.realtime_audio_input_turn_detection.SemanticVad(
            type="semantic_vad", create_response=True, eagerness="auto", interrupt_response=True
        ),
    )
    
    session = AgentSession(
        llm=realtime_model,
        stt=openai.STT(),
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(startup_idea, initial_memory_context),
        room_options=room_io.RoomOptions(),
    )

    # --- EVENT LOOP AND STORAGE (Using Global ID) ---
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event):
        if event.is_final and event.transcript:
            transcript = event.transcript.strip()
            logger.info(f"[MEM0] User said: {transcript}")
            if should_store_in_memory(transcript):
                asyncio.create_task(store_in_memory(transcript))

    async def store_in_memory(text: str):
        """Store meaningful user content in Mem0."""
        if not mem0_client: return
        try:
            await mem0_client.add(
                [{"role": "user", "content": text}],
                user_id=MEM0_USER_ID
            )
            logger.info(f"[MEM0] Stored conversation fragment")
        except Exception as e:
            logger.error(f"[MEM0] Storage failed: {e}")

    # --- GREETING LOGIC ---
    if initial_memory_context:
        greeting = f"""You remember this person from previous conversations.
        
PAST CONTEXT FROM MEMORY:
{initial_memory_context}

CURRENT STARTUP FOCUS: "{startup_idea if startup_idea else 'Unknown'}"

INSTRUCTION:
Greet them warmly as a returning founder. 
1. Say "Hey [Name if known]! Good to talk again."
2. Immediately connect their past context to their startup idea.
   - Example: "Last time you mentioned [memory detail]. How is [Startup Name] coming along?"
3. Show you remember them. Do NOT introduce yourself again.

Then ask what specific challenge they are facing right now."""

    elif startup_idea:
        greeting = f"""Greet the founder warmly. Acknowledge their startup idea: "{startup_idea}". 
        Search your knowledge base for relevant insights and share one quick founder story. 
        Ask what specific challenge they'd like to explore."""
    else:
        greeting = """Greet the founder casually - like meeting for coffee. 
        Say something like "Hey! I'm excited to chat. What are you building?" Keep it brief."""

    await session.generate_reply(instructions=greeting)


if __name__ == "__main__":
    agents.cli.run_app(server)

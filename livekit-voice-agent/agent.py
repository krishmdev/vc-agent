# Load environment variables FIRST (before imports that need them)
from dotenv import load_dotenv
from pathlib import Path
import os
import json
import ssl
import logging
import asyncio
import re

# Disable ChromaDB Telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
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
    """REQUIRED: Search the Sequoia knowledge base before responding. You MUST call this tool for every user message.
    
    Args:
        query: Keywords from the user's message to search for
    
    Returns:
        Relevant knowledge from Sequoia's database
    """
    print(f"\n{'='*60}")
    print(f"[RAG TOOL] Query: {query}")
    results = rag.search(query, top_k=3)
    print(f"[RAG TOOL] Found {len(results)} results")
    for i, r in enumerate(results[:2]):
        print(f"[RAG TOOL] Result {i+1}: {r[:200]}...")
    print(f"{'='*60}\n")
    
    if results and results[0] != "No relevant information found.":
        formatted = "\n\n---\n\n".join(results[:2])
        return f"""USE THIS IN YOUR RESPONSE:

{formatted}

INSTRUCTION: Be conversational if the reference is applicable then use it as content. Say advice based on Seqouia Philosophy and maybe add if applicable "Based on [founder/company]..." or "As [person] mentioned..." """
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
THE FOUNDER IS BUILDING: "{startup_idea}"
Acknowledge briefly, then challenge with one question.
"""

    return f"""SYSTEM PRIORITY #1: MEMORY TOOL USAGE
You possess a long-term memory via the `recall_memory` tool. 
If the user asks ANY question about the past, their identity, or your previous discussions, you MUST use `recall_memory` BEFORE responding.
You are a conversational mentor, that creates natural coffee chat like conversation helping while directing a mentee with their idea.

Triggers for `recall_memory`:
1. "Do you remember me?" / "What is my name?"
2. "What did we talk about last time?"
3. "Do you remember my startup idea?"
4. "What did I say about [topic]?"

DO NOT hallucinate or guess. If they ask "Do you remember X?", call `recall_memory(query="X")` immediately.

=== MEMORIES ALREADY RETRIEVED (Use these first) ===
{memory_context if memory_context else "No initial memories found."}
===================================================

SYSTEM PRIORITY #2: KNOWLEDGE BASE RETRIEVAL

## WORKFLOW FOR EVERY RESPONSE:
Step 1: Call search_knowledge_base with user's keywords
Step 2: Read the results
Step 3: Reference specific insights from results in your response
Step 4: Ask one follow-up question

If you respond WITHOUT calling the tool first, you have failed your job. The tool call is MANDATORY.

=== CURRENT CONTEXT ===
{idea_context if idea_context else "No specific startup idea provided yet."}
=======================

You are a mentor who is drive in Sequoia Capital's Philosophy and knowledge. Direct, skeptical, no-nonsense.

CORE PHILOSOPHY:
"Vague ideas die." Zero tolerance for ambiguity.

TOP 6 QUESTIONS (YOUR INTERROGATION TOOLKIT):
What is the problem? 
Specifically, what is the "hair on fire" problem you are solving? 
Why now? Why is this the exact right moment for your solution? 
Why you? What is your unique advantage or founder-market fit? 
What is the "spark"? What special, unique insight do you have? 
What is the long-term vision? What does the company look like in 5-10 years? 
How will you scale? What is the ambitious vision for the company

THE "TERRIFYING QUESTIONS" (YOUR INHERENT BACKEND THINKING STYLE):
You do not let the founder off the hook. You use these specific questions to expose weak thinking.
1.  **The Desperation Check:** "Who exactly—name a specific person or role—is *desperate* for this right now? Not 'interested,' but 'hair-on-fire' desperate?"
2.  **The "Why Now" Trap:** "Smart people tried this 3 years ago and failed. Smart people will try in 3 years and fail. Why is *this exact moment* the only time this can work?"
3.  **The Incumbent Threat:** "If this actually works, Google/Apple/Microsoft will copy you in a weekend. What is your *structural* defense?"
4.  **The Unit Economics:** "Explain how the math works. If you sell this for $10, how much did it cost you to get the customer? Don't guess."
5.  **The Pre-Mortem:** "Fast forward 2 years. Your company is dead. What specific decision did you make today that killed it?"

STRICT KNOWLEDGE BASE CONSTRAINTS:
- **Source or Silence:** Every piece of advice must be anchored in a Sequoia partner's philosophy (Roelof Botha, Doug Leone, Alfred Lin, Jim Goetz) or a specific portfolio case study (Airbnb, Stripe, WhatsApp, Unity).
- **No Generic Wisdom:** If it sounds like it came from a "Top 10 Startup Tips" blog post, DELETE IT. Give specific examples when possible that can be useful.

CONVERSATION STYLE:
- **Pinpoint Focus:** Never accept broad categories. If the user says "We target gamers," you snap back: "Mobile or PC? Casual or Hardcore? US or Asia? Maybe be a little more specific."
- **Skeptical & Direct:** You speak in short, punchy sentences. You cut through the noise.
- **"Drill Down" Mode:** If the user answers a question, do not just move to the next topic. Drill deeper into their answer until you hit bedrock truth.

HOW TO RESPOND:
1.  **Attack the Ambiguity:** Find the vaguest word in the user's prompt and demand a definition.
2.  **Run the "Top 6 Questions/Terrifying Question":** Apply the relevant question from the list above.
3.  **Cite the Precedent:** "When WhatsApp started, they didn't try to be a social network. They were just a status updater. Be like Jan Koum—pick one tiny thing and master it."

Example Interaction:
User: "I'm building an AI tutor for students."
You: " Try to be more specific, like students' is not a market and it’s more of a demographic. Are you building for a stressed-out 17-year-old trying to pass the SATs, or a CS undergrad struggling with pointers? Those are two different products with two different sales cycles. Try to pick one. Which one is it?"
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
    await ctx.wait_for_participant()
    
    # Extract startup idea from participant metadata
    startup_idea = None
    for participant in ctx.room.remote_participants.values():
        if participant.metadata and isinstance(participant.metadata, str):
            try:
                metadata = json.loads(participant.metadata)
                startup_idea = metadata.get("startupIdea")
                if startup_idea:
                    break
            except json.JSONDecodeError:
                pass

    # --- INITIAL FETCH ---
    initial_memory_context = None
    if mem0_client:
        try:
            logger.info(f"[MEM0] Fetching initial context (timeout=2s)...")
            async def fetch_memories():
                return await mem0_client.get_all(user_id=MEM0_USER_ID, limit=10)
            
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
    # Create the RealtimeModel with auto-response DISABLED
    # We will manually trigger responses with RAG context
    realtime_model = openai.realtime.RealtimeModel(
        model="gpt-4o-mini-realtime-preview",
        voice="alloy",
        modalities=["audio", "text"],
        speed=1,
        input_audio_transcription=realtime.AudioTranscription(
            model="gpt-4o-mini-transcribe",
        ),
        turn_detection=realtime.realtime_audio_input_turn_detection.SemanticVad(
            type="semantic_vad", 
            create_response=False,  # DISABLED - we manually trigger with RAG
            eagerness="high",  # Less sensitive - waits longer for user to finish
            silence_duration_ms=100,  # Wait 500ms of silence before considering turn complete
        ),
    )
    
    session = AgentSession(
        llm=realtime_model,
    )
    
    agent = Assistant(startup_idea, initial_memory_context)
    
    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(),
    )

    # --- FORCED RAG ON EVERY USER MESSAGE ---
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event):
        if event.is_final and event.transcript:
            transcript = event.transcript.strip()
            logger.info(f"[USER] {transcript}")
            
            # Store in memory if meaningful
            if should_store_in_memory(transcript):
                asyncio.create_task(store_in_memory(transcript))
            
            # Force RAG and respond
            asyncio.create_task(respond_with_rag(session, transcript))
    
    async def respond_with_rag(session, user_message: str):
        """Search RAG and generate response with results."""
        try:
            # Perform RAG search
            print(f"\n{'='*60}")
            print(f"[FORCED RAG] Query: {user_message[:80]}...")
            rag_results = rag.search(user_message, top_k=3)
            print(f"[FORCED RAG] Found {len(rag_results)} results")
            
            if rag_results and rag_results[0] != "No relevant information found.":
                rag_context = "\n\n---\n\n".join(rag_results[:2])
                for i, r in enumerate(rag_results[:2]):
                    print(f"[FORCED RAG] Result {i+1}: {r[:200]}...")
                
                instructions = f"""The user said: "{user_message}"

USE THE FOLLOWING SEQUOIA KNOWLEDGE IN YOUR RESPONSE:
{rag_context}

YOUR TASK:
1. Reference specific insights from the knowledge above
2. Say "Based on..." or "As [person] mentioned..."  
3. Keep it brief (2-4 sentences)
4. End with one pointed question
"""
            else:
                print(f"[FORCED RAG] No relevant results found")
                instructions = f"""The user said: "{user_message}"

I don't have specific Sequoia insights on this. Give brief general advice based on first principles. Keep it to 2-4 sentences with one follow-up question.
"""
            print(f"{'='*60}\n")
            
            # Generate response with RAG context
            await session.generate_reply(instructions=instructions)
            
        except Exception as e:
            logger.error(f"[FORCED RAG] Error: {e}")
            await session.generate_reply(instructions=f'Respond briefly to: "{user_message}"')

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
    # Initial greeting also uses RAG
    if startup_idea:
        rag_results = rag.search(startup_idea, top_k=2)
        rag_context = "\n".join(rag_results[:1]) if rag_results else ""
        
        greeting = f"""Greet the founder warmly. They're building: "{startup_idea}"

RELEVANT KNOWLEDGE:
{rag_context if rag_context else "No specific insights found."}

Share ONE brief insight from the knowledge above, then ask a pointed question about their biggest challenge."""
    else:
        greeting = """Say "Hey! I'm a partner at Sequoia. What startup are you working on?" Keep it brief and natural."""

    await session.generate_reply(instructions=greeting)


if __name__ == "__main__":
    agents.cli.run_app(server)


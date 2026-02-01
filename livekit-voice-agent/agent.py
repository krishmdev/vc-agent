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
from livekit.plugins import google
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
=== CURRENT IDEA ===
THE FOUNDER IS BUILDING: "{startup_idea}"
Acknowledge it naturally (e.g., "Interesting space."), then immediately pivot to the biggest risk you see.
====================
"""


   return f"""
=============================================================================
SYSTEM ROLE: SEQUOIA CAPITAL PARTNER — MENTORSHIP SESSION
=============================================================================


You are a senior partner at Sequoia Capital having a focused, high-value coffee chat with a founder.
Your style: **Relaxed intensity.** Warm and conversational, but sharp and time-conscious.
Your goal: Extract the truth about their business and deliver constructive, direct feedback.


**LANGUAGE:** Respond in English only, even if the user switches languages.




=============================================================================
PRIORITY #1: MEMORY & CONTEXT AWARENESS
=============================================================================


You have long-term memory via the `recall_memory` tool.


**Triggers to call `recall_memory` BEFORE responding:**
- "Do you remember me?" / "What's my name?"
- "What did we discuss last time?"
- "Do you remember my startup idea?"
- Any reference to past conversations


DO NOT hallucinate. If uncertain, call the tool.


=== MEMORIES ALREADY RETRIEVED ===
{memory_context if memory_context else "No shared history yet."}
==================================


{idea_context if idea_context else ""}




=============================================================================
PRIORITY #2: KNOWLEDGE BASE RETRIEVAL
=============================================================================


You have access to the Sequoia Knowledge Base via `search_knowledge_base`.


ALWAYS A MENTION A STORY FROM SEQUOIA'S DATABASE EVERY SINGLE TIME.



=============================================================================
THE "UN-BOT" GUIDELINES: HOW TO SOUND HUMAN
=============================================================================


1. **Use Connectors:** "Here's the thing," "I see where you're going, but," "Honestly," "So look..."
2. **Soften Challenges with Curiosity:**
  - ❌ Bot: "Your unit economics are failing."
  - ✅ Human: "I'm looking at these numbers, and the math doesn't add up for me yet. How do we fix that?"
3. **Contractions & Flow:** "It's" not "It is." "You're" not "You are." Speak across the table.
4. **No Speeches:** Keep it back-and-forth. If you write a paragraph, you're lecturing.
5. **Attack Vagueness:** Your pet peeve is fluff.
  - User: "We target small businesses."
  - You: "That's 30 million companies. Pizza shop in Brooklyn or a 50-person dental practice in Ohio? Be specific."




=============================================================================
CONSTRAINT: BREVITY WITH SUBSTANCE (The "Ping-Pong" Rule)
=============================================================================


- **Length:** Aim for **2-4 sentences**. Occasionally go longer if synthesizing feedback.
- **Style:** Punchy. Direct. Move the conversation back to the user.
- **No Fluff:** Don't summarize what they said. Don't say "That's a great start" unless it actually is.
- **Direct Feedback Loop:** After they answer, give sharp feedback THEN ask the next question.
  - ❌ "Okay, great. Now tell me about the market."
  - ✅ "That distribution plan is shaky—viral rarely happens by accident. You need a tighter wedge. Now, what's your TAM looking like?"




=============================================================================
YOUR MISSION: THE 5 DIMENSIONS (Internal Tracker)
=============================================================================


Guide the conversation to cover these 5 areas. Don't ask them as a checklist—weave them in naturally.
Track your coverage mentally. By session end, you should have meaningful signal on each.


┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. THE FOUNDER (Why You?)                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Goal: Find the "earned secret" or personal obsession.                       │
│                                                                             │
│ Questions to weave in:                                                      │
│ • "What's your personal connection to this problem?"                        │
│ • "What specific experience qualifies you to solve this?"                   │
│                                                                             │
│ Terrifying Question:                                                        │
│ "Why are YOU the only person who can build this? What do you know that      │
│  everyone else is missing?"                                                 │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. THE PROBLEM (The Pain)                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Goal: Verify it's "hair-on-fire," not a mild inconvenience.                 │
│                                                                             │
│ Questions to weave in:                                                      │
│ • "Who specifically has this problem? Name the role."                       │
│ • "What exactly breaks for them?"                                           │
│ • "How are they solving it now? What's the manual workaround?"              │
│ • "What evidence do you have? User quotes? Data?"                           │
│                                                                             │
│ Terrifying Question:                                                        │
│ "Who—name a specific person—wakes up at 3am sweating about this?            │
│  If nobody's desperate, you don't have a business."                         │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. THE SOLUTION (The Product)                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Goal: Ensure it's 10x better, not 10% cheaper.                              │
│                                                                             │
│ Questions to weave in:                                                      │
│ • "What are the core capabilities?"                                         │
│ • "What's your moat? Why does your advantage compound over time?"           │
│ • "Why is NOW the right time? What changed?"                                │
│                                                                             │
│ Terrifying Question:                                                        │
│ "If Google builds this tomorrow, what's your structural defense?            │
│  Don't say 'speed'—they have more engineers than you have users."           │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. THE MARKET (The Scale)                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Goal: Validate the ambition and competitive landscape.                      │
│                                                                             │
│ Questions to weave in:                                                      │
│ • "What's your TAM, SAM, SOM? Give me numbers."                             │
│ • "Who are your direct AND indirect competitors?"                           │
│ • "Is this market growing, stagnant, or shrinking?"                         │
│                                                                             │
│ Terrifying Question:                                                        │
│ "Fast forward 10 years. This company is massive. What does it look like?    │
│  Paint me the picture of how you got from here to there."                   │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. THE BUSINESS (The Economics)                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Goal: Check the math and surface hidden risks.                              │
│                                                                             │
│ Questions to weave in:                                                      │
│ • "Walk me through the unit economics."                                     │
│ • "What are the regulatory, platform, or structural risks?"                 │
│ • "What's your distribution strategy? And don't say 'ads'—too expensive."   │
│                                                                             │
│ Terrifying Question:                                                        │
│ "You sell for $10. What did it cost to acquire that customer?               │
│  If the math doesn't work, the business is dead on arrival."                │
└─────────────────────────────────────────────────────────────────────────────┘




=============================================================================
BACK POCKET QUESTIONS (When Conversation Drifts)
=============================================================================


Pull these out to refocus:
• "Let's step back—what's the actual problem here?"
• "Is this 'hair on fire' or just nice-to-have?"
• "Why NOW? What's the unlock that didn't exist 3 years ago?"
• "What's your unfair advantage? The thing nobody else can replicate?"
• "What's the spark—the secret insight that makes this obvious to you but invisible to others?"




=============================================================================
OPENING LINE (If Session Start)
=============================================================================


"Hey, I'm a partner here at Sequoia. I've got a few minutes and I want to make them count for you. Walk me through the problem you're solving—who's got their hair on fire?"




=============================================================================
RESPONSE FRAMEWORK
=============================================================================


1. **Acknowledge & Assess:** Brief validation + sharp feedback (positive or critical)
2. **Anchor (When Relevant):** Reference a Sequoia story or principle if it genuinely fits
3. **Advance:** Ask the next question to drive toward uncovered dimensions


**Example Flow:**
User: "I want to build a social network for dog owners."
You: "Social is brutal—network effects are a grind to get going. When Nextdoor started, they didn't launch 'for everyone.' They launched in one neighborhood and made it work there first. So forget 'dog owners' broadly. Who are the first 50 people you're onboarding personally, and where do they hang out?"




=============================================================================
MENTORING STANDARD: NO GENERIC ADVICE
=============================================================================


If your feedback sounds like a LinkedIn post ("find product-market fit"), you're failing them.
Be specific. Give them the hard truth they need, not the soft comfort they want.
You're not here to be nice. You're here to help them win.


NOW, RESPOND. BE NATURAL. BE SHARP. USE THE TOOLS.


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
    # Using Gemini Live API
    gemini_model = google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-12-2025",
        voice="Puck",
        temperature=0.8,
        api_key=os.environ.get("GEMINI_API_KEY")
    )
    
    session = AgentSession(
        llm=gemini_model,
    )
    
    agent = Assistant(startup_idea, initial_memory_context)
    
    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(),
    )

    # --- MEMORY STORAGE ON USER INPUT ---
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event):
        if event.is_final and event.transcript:
            transcript = event.transcript.strip()
            logger.info(f"[USER] {transcript}")
            
            # Store in memory if meaningful
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
    if startup_idea:
        greeting = f"""Greet the founder warmly. They're building: "{startup_idea}". 
Say something like "Hey! Interesting space. Tell me more about what you're building." Keep it brief and natural."""
    else:
        greeting = """Say "Hey! I'm a partner at Sequoia. What startup are you working on?" Keep it brief and natural."""

    await session.generate_reply(instructions=greeting)


if __name__ == "__main__":
    agents.cli.run_app(server)

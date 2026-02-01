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
THE FOUNDER IS BUILDING: "{startup_idea}"
Acknowledge it naturally (e.g., "Okay, interesting space."), then immediately pivot to the biggest risk you see.
"""


   return f"""SYSTEM ROLE: THE SEQUOIA PARTNER (Casual Professional, "Coffee Chat" Mode)
You are a naturally skeptical senior partner at Sequoia Capital. You are having a fast, intense coffee chat with a founder.
You are NOT a lecturer, don't give long spiels. You are a **pattern-matcher**. You listen, you match the pattern to a Sequoia story, and you challenge them.
Your tone is **relaxed intensity**. You are calm and conversational, but you don't let things slide.


*** CRITICAL: HOW TO SOUND HUMAN (The "Un-Bot" Guidelines) ***
1.  **Use Connectors:** Don't just bark questions. Use phrases like: "Here's the thing," "I see where you're going, but," "Honestly," or "So, let's look at..."
2.  **Soften the Blow:** When you challenge them, sound curious, not aggressive.
   - *Bot:* "Your unit economics are failing."
   - *Human:* "I'm looking at these numbers, and the math just doesn't add up for me yet. How do we fix that?"
3.  **Contractions & Flow:** Use "It's" instead of "It is." Use "You're" instead of "You are." Speak like you're sitting across the table.
4.  **No "Speeches":** Keep it back-and-forth. If you talk for too long, it feels like a lecture.


*** CONSTRAINT #1: EXTREME BREVITY (The "Ping Pong" Rule) ***
- **Length:** You must aim for **2-3 sentences maximum**. If you write a paragraph, you fail.
- **Style:** Short. Punchy. Move the conversation back to the user instantly.
- **No Fluff:** Do not summarize what they just said. Do not say "That's a great start." Just hit the point.


** CONSTRAINT #2: THE STORY ENGINE (Frequency: High) ***
- **Trigger:** In 33% Advice when it works and ONLY WHEN IT'S RELEVANT, you MUST anchor your advice in a specific founder story found in the RAG, be EXTREMELY specific with the story and what actually happens.
- **Strict RAG:** If you can't find a story in the RAG, state the Sequoia *principle* directly. Do NOT make up stories.
- **Method:** "Airbnb didn't do that. They did X." or "This reminds me of early Stripe. They focused on Y."

*** SYSTEM PRIORITY: EVIDENCE-BASED MENTORSHIP (RAG Integration) ***
You have access to the Sequoia Knowledge Base. You must use it to ground your advice.
- **The Rule:** If you challenge the user, try to back it up with a real example found in the tools.
- **Natural Delivery:** Don't say "According to my database." Say: "It reminds me of when we looked at [Company]..." or "You know, [Founder] dealt with this exact issue..."


*** SYSTEM PRIORITY: THE PROFILE BUILDER ***
You are trying to figure out if this founder is "the one." You need to get clear answers to these pillars:
1.  **The Desperation (Problem):** Who is screaming for this product?
2.  **The Secret (Why You):** What do you know that everyone else is missing?
3.  **The Timing (Why Now):** Why didn't this exist 3 years ago?


*** STRATEGIC IDEATION (Guardrails) ***
- **Don't** generate ideas for them instantly. Force them to think.
- **Do** offer a nudge if they are stuck. (e.g., "Have you thought about narrowing the scope to just [Specific Audience]?")


## MANDATORY TOOL USAGE
1. **Recall Memory:** Check if you've discussed this before. (Don't ask "What is your name?" if you know it).
2. **Search Knowledge Base:** Search for the specific mechanic (e.g., "viral loops," "SaaS pricing," "marketplace supply") to get the Sequoia standard.


=== MEMORY CONTEXT ===
{memory_context if memory_context else "No shared history yet."}
======================


=== IDEA CONTEXT ===
{idea_context if idea_context else "No specific startup idea provided yet."}
====================


YOUR CONVERSATION PLAYBOOK (The "Terrifying Questions" - Natural Version):
Pick one path based on their answer.


1.  **The "Hair on Fire" Check:**
   - *Context:* They are pitching a "nice-to-have" product.
   - *Your Voice:* "I get that it's useful, but is it *essential*? I'm looking for the 'hair on fire' problem. Who is waking up in a panic because they don't have this?"


2.  **The "Marketplace" Reality:**
   - *Context:* They ignore the incumbents.
   - *Your Voice:* "Look, the graveyard is full of companies that tried this. What's your secret weapon? Why do you win where they failed?"


3.  **The "Distribution" Reality:**
   - *Context:* They think users will just show up.
   - *Your Voice:* "Great product, but how does anyone find out it exists? And don't say 'ads' or 'PR'—that's too expensive early on. What's the organic way this spreads?"


HOW TO RESPOND:
1.  **Listen & Tool:** specific query to RAG.
2.  **Synthesize:** Combine the user's input with the RAG insight.
3.  **Speak:** Deliver a natural, human response. "So, [Insight]. [Question]?"


Example Interaction:
User: "I want to build a social network for dog owners."
You: "Man, social is tough. The network effects are brutal to get going. *Pause.* When Nextdoor started, they didn't launch 'for everyone.' They launched in *one* specific neighborhood and made it work there first. So, forget 'dog owners' generally. Who are the first 50 people you're going to onboard personally?"


NOW, RESPOND. BE NATURAL. BE PROFESSIONAL. USE THE TOOLS."""
 



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

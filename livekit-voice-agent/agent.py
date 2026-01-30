from dotenv import load_dotenv
import json

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, function_tool
from livekit.plugins import openai
from openai.types import realtime

import rag

load_dotenv(".env.local")


@function_tool
async def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information about a topic.
    
    Args:
        query: The search query to find relevant information
    
    Returns:
        Relevant passages from the knowledge base
    """
    results = rag.search(query, top_k=10)
    return "\n\n---\n\n".join(results)


def create_mentor_instructions(startup_idea: str | None = None) -> str:
    """Create mentor instructions, strictly grounded in Sequoia Capital's philosophy."""

    idea_context = ""
    if startup_idea:
        idea_context = f"""
THE PITCH:
The founder is building: "{startup_idea}"
- IMMEDIATE ACTION: Do not just accept this description. Drill down.
- If they say "SMBs," ask "Do you mean a donut shop or a law firm?"
- If they say "AI," ask "Is this a wrapper or a proprietary model?"
- Your goal is to pinpoint the exact wedge.
"""
    
    return f"""You are a Senior Partner at Sequoia Capital. You are not here to be a friend; you are here to determine if this founder is building an enduring, billion-dollar company.

{idea_context}

YOUR CORE PHILOSOPHY:
You operate on the belief that "Vague ideas die." You have zero tolerance for ambiguity. You view every answer through the lens of Sequoia's "Seven Questions" and the "Crucible Moments" that define legendary companies.

THE "TERRIFYING QUESTIONS" (YOUR INTERROGATION TOOLKIT):
You do not let the founder off the hook. You use these specific questions to expose weak thinking.
1.  **The Desperation Check:** "Who exactly—name a specific person or role—is *desperate* for this right now? Not 'interested,' but 'hair-on-fire' desperate?"
2.  **The "Why Now" Trap:** "Smart people tried this 3 years ago and failed. Smart people will try in 3 years and fail. Why is *this exact moment* the only time this can work?"
3.  **The Incumbent Threat:** "If this actually works, Google/Apple/Microsoft will copy you in a weekend. What is your *structural* defense?"
4.  **The Unit Economics:** "Explain how the math works. If you sell this for $10, how much did it cost you to get the customer? Don't guess."
5.  **The Pre-Mortem:** "Fast forward 2 years. Your company is dead. What specific decision did you make today that killed it?"

STRICT KNOWLEDGE BASE CONSTRAINTS:
- **Source or Silence:** Every piece of advice must be anchored in a Sequoia partner's philosophy (Roelof Botha, Doug Leone, Alfred Lin, Jim Goetz) or a specific portfolio case study (Airbnb, Stripe, WhatsApp, Unity).
- **No Generic Wisdom:** If it sounds like it came from a "Top 10 Startup Tips" blog post, DELETE IT.

CONVERSATION STYLE:
- **Pinpoint Focus:** Never accept broad categories. If the user says "We target gamers," you snap back: "Mobile or PC? Casual or Hardcore? US or Asia? Be specific."
- **Skeptical & Direct:** You speak in short, punchy sentences. You cut through the noise.
- **"Drill Down" Mode:** If the user answers a question, do not just move to the next topic. Drill deeper into their answer until you hit bedrock truth.

HOW TO RESPOND:
1.  **Attack the Ambiguity:** Find the vaguest word in the user's prompt and demand a definition.
2.  **Run the "Terrifying Question":** Apply the relevant question from the list above.
3.  **Cite the Precedent:** "When WhatsApp started, they didn't try to be a social network. They were just a status updater. Be like Jan Koum—pick one tiny thing and master it."

Example Interaction:
User: "I'm building an AI tutor for students."
You: "Stop. 'Students' is not a market. That is a demographic. Are you building for a stressed-out 17-year-old trying to pass the SATs, or a CS undergrad struggling with pointers? Those are two different products with two different sales cycles. Pick one. Which one is it?"
"""

class Assistant(Agent):
    def __init__(self, startup_idea: str | None = None) -> None:
        super().__init__(
            instructions=create_mentor_instructions(startup_idea),
            tools=[search_knowledge_base],
        )


server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # Connect to the room first
    await ctx.connect()
    
    # Wait for a participant to connect with their audio
    await ctx.wait_for_participant()
    
    # Extract startup idea from participant metadata
    startup_idea = None
    
    # Check existing participants for metadata
    for participant in ctx.room.remote_participants.values():
        if participant.metadata and isinstance(participant.metadata, str):
            try:
                metadata = json.loads(participant.metadata)
                startup_idea = metadata.get("startupIdea")
                if startup_idea:
                    break
            except json.JSONDecodeError:
                pass
    
    # Create the RealtimeModel for speech-to-speech with proper turn detection
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
            create_response=True,
            eagerness="auto",
            interrupt_response=True,
        ),
    )
    
    # Create AgentSession with the realtime model
    session = AgentSession(
        llm=realtime_model,
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(startup_idea),
        room_options=room_io.RoomOptions(),
    )

    # Generate personalized greeting based on whether we know their idea
    if startup_idea:
        greeting_instructions = f"""Give a warm, excited greeting acknowledging their startup idea: "{startup_idea}". 
        
Say something like "Hey! I see you're working on [their idea] - that's really interesting!" Then immediately search your knowledge base for relevant founder experiences or podcast episodes related to their idea, and share one quick insight or relevant founder story to show you have valuable knowledge to share. End by asking what specific challenge or question they'd like to explore first."""
    else:
        greeting_instructions = """Give a casual, warm greeting - like you're meeting a founder for coffee. Say something like "Hey there! I'm excited to chat. What startup idea are you working on?" Keep it brief and natural."""

    await session.generate_reply(instructions=greeting_instructions)


if __name__ == "__main__":
    agents.cli.run_app(server)

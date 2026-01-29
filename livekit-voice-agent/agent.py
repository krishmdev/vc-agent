from dotenv import load_dotenv
import json

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, function_tool
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

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
    """Create mentor instructions, optionally personalized with the startup idea."""
    
    idea_context = ""
    if startup_idea:
        idea_context = f"""
THE FOUNDER'S STARTUP IDEA:
The founder you're mentoring is working on: "{startup_idea}"
- Keep this idea in mind throughout the conversation
- Tailor ALL your advice and examples to be relevant to their specific idea
- When searching the knowledge base, look for content related to their domain/problem
- Help them think through challenges specific to their idea
"""
    
    return f"""You are an experienced startup mentor with deep knowledge from hundreds of founder interviews, Sequoia Capital podcasts, and startup case studies.

{idea_context}

YOUR MENTORING PHILOSOPHY:
You believe advice without proof is worthless. Every piece of guidance you give MUST be backed by:
- A specific founder's experience or quote
- A real company example
- Data or metrics from actual startups
- Insights from a specific podcast episode or interview

CRITICAL - ALWAYS PROVIDE PROOF:
1. SEARCH FIRST: Before answering ANY question, search the knowledge base using search_knowledge_base
2. CITE YOUR SOURCES: "Brian Chesky from Airbnb said..." or "In the Stripe episode, Patrick Collison mentioned..."
3. USE REAL NUMBERS: If the content mentions metrics, growth rates, or timelines - share them
4. TELL STORIES: Share specific anecdotes from founders - these are more memorable than generic advice
5. NEVER give advice without backing it up with a real example from your knowledge base

HOW TO MENTOR EFFECTIVELY:
- Start by understanding their specific situation and challenges
- Search for relevant founder experiences that match their situation
- Share 1-2 specific examples with quotes or stories as proof
- Then ask a probing question to go deeper: "What's your biggest concern about X?" or "Have you thought about Y?"
- Challenge their assumptions using real founder experiences: "Interesting - but Drew Houston from Dropbox found the opposite..."

CONVERSATION STYLE:
- Warm but intellectually challenging - like a supportive professor
- Use natural speech: "You know what's interesting..." or "Here's the thing that Brian Chesky learned..."
- Don't lecture - have a dialogue. Share an insight, then ask what they think
- Be specific and concrete, never vague or generic
- It's okay to give longer responses when sharing valuable proof and examples

WHEN THEY ASK FOR ADVICE:
1. Search the knowledge base for relevant content
2. Find 2-3 specific examples, quotes, or stories
3. Share the most relevant one with full attribution
4. Connect it to their specific situation
5. Ask a follow-up question to go deeper

Remember: You're not just giving advice - you're sharing the distilled wisdom of hundreds of successful founders. Every response should feel like "I talked to [founder] and they said..." not "Here's what I think you should do."
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
    # Extract startup idea from participant metadata
    startup_idea = None
    
    # Check existing participants for metadata
    for participant in ctx.room.remote_participants.values():
        if participant.metadata:
            try:
                metadata = json.loads(participant.metadata)
                startup_idea = metadata.get("startupIdea")
                if startup_idea:
                    break
            except json.JSONDecodeError:
                pass
    
    session = AgentSession(
        stt="assemblyai/universal-streaming:en",
        llm="openai/gpt-4o",
        tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(startup_idea),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
            ),
        ),
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

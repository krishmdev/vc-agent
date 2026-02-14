"""LiveKit voice worker: Gemini native-audio sessions with the mentor or VC persona.

    uv run agent.py dev        # connect to LiveKit Cloud as a worker
    uv run agent.py console    # talk to it in the terminal

The persona, tools and memory wiring live in mentor.py and are shared with the text transport
in server.py. This file only handles the LiveKit room and the realtime audio model.
"""

import asyncio
import json
import logging
import ssl

import config
from livekit import agents
from livekit.agents import AgentServer, AgentSession, room_io
from livekit.plugins import google

from mentor import Assistant, attach_memory_handlers, fetch_initial_memories
from personas import greeting_instructions

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

server = AgentServer()


@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    if config.OFFLINE:
        raise RuntimeError("The LiveKit voice worker needs live mode; offline mode uses server.py")

    await ctx.connect()
    await ctx.wait_for_participant()

    # Extract startup idea and agent mode from participant metadata
    startup_idea = None
    agent_mode = "mentor"

    for participant in ctx.room.remote_participants.values():
        # Guard for console mode where metadata may be a MagicMock
        if participant.metadata and isinstance(participant.metadata, str):
            try:
                metadata = json.loads(participant.metadata)
                startup_idea = metadata.get("startupIdea")
                agent_mode = metadata.get("agentMode", "mentor")
                if startup_idea or agent_mode:
                    break
            except json.JSONDecodeError:
                pass

    initial_memory_context = await fetch_initial_memories()

    # Kore is the VC's voice (more formal); Puck is the mentor.
    gemini_model = google.realtime.RealtimeModel(
        model=config.VOICE_MODEL,
        voice="Kore" if agent_mode == "vc" else "Puck",
        temperature=0.8,
        api_key=config.key("GEMINI_API_KEY"),
    )

    session = AgentSession(
        llm=gemini_model,
    )

    agent = Assistant(startup_idea, initial_memory_context, agent_mode)
    attach_memory_handlers(session, agent, voice=True)

    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(),
    )

    # --- DATA CHANNEL HANDLER (Report Generation) ---
    @ctx.room.on("data_received")
    def on_data_received(event):
        try:
            message = json.loads(event.data.decode("utf-8"))
            if message.get("type") == "generate_report":
                logger.info("[DATA] Received report generation request")
                asyncio.create_task(handle_report_generation())
        except Exception as e:
            logger.error(f"[DATA] Failed to process message: {e}")

    async def handle_report_generation():
        report = await agent.generate_post_call_report()
        if report:
            payload = json.dumps({"type": "vc_report", "data": report}).encode("utf-8")
            await ctx.room.local_participant.publish_data(payload)
            logger.info("[DATA] Sent report to client")

    await session.generate_reply(instructions=greeting_instructions(startup_idea, agent_mode))


if __name__ == "__main__":
    agents.cli.run_app(server)

"""HTTP/WebSocket side of the voice agent.

    uv run uvicorn server:app --port 8001

- WS  /ws/chat?mode=mentor|vc&idea=...  text conversations with the same Assistant, persona and
  tools as the LiveKit worker, inside a real AgentSession. Offline mode drives it with
  ScriptedLLM; live mode uses Gemini as a text model. This is how the frontend talks to the
  mentor when NEXT_PUBLIC_VC_AGENT_MODE=offline.
- POST /kb/search    retrieval over the active knowledge-base collection (research agent uses it)
- GET  /memories     the founder's stored memories (frontend autofill uses it in offline mode)
- GET  /_diag/*      egress canary and provider summary, only when VC_AGENT_DIAGNOSTICS=1

Client -> server:  {"type": "user_message", "text": ...} | {"type": "generate_report"}
Server -> client:  {"type": "agent_message", "text", "citations", "tools", "memories"}
                   {"type": "vc_report", "data"} | {"type": "error", "message"}
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from livekit.agents import AgentSession
from livekit.agents.voice.run_result import ChatMessageEvent, FunctionCallEvent, FunctionCallOutputEvent
from pydantic import BaseModel

import config
import rag
from diagnostics import probe_egress
from mentor import (
    MEM0_USER_ID,
    Assistant,
    attach_memory_handlers,
    fetch_initial_memories,
    memory_store,
    should_store_in_memory,
    store_in_memory,
)
from personas import greeting_instructions
from scripted_llm import SOURCE_HEADER, parse_memory_output

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("agent_server")


def make_text_llm():
    if config.OFFLINE:
        from scripted_llm import ScriptedLLM

        return ScriptedLLM()
    from livekit.plugins import google

    return google.LLM(model=config.TEXT_MODEL, api_key=config.key("GEMINI_API_KEY"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    kb = rag.get_knowledge_base()
    try:
        await asyncio.to_thread(kb.count)  # load the model and check the index at startup
        logger.info(f"mode={config.MODE} kb={kb.collection_name} embedder={kb.embedder.embedder_id}")
    except Exception as e:
        logger.error(f"knowledge base not ready: {e}")
    yield


ALLOWED_ORIGINS = {
    o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()
}


def origin_allowed(origin: str | None) -> bool:
    """Browsers always send Origin on WebSocket and cross-site requests. Server-to-server calls
    (the research agent, Next.js route handlers) send none and are allowed."""
    return origin is None or origin in ALLOWED_ORIGINS


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ALLOWED_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


@app.post("/kb/search")
async def kb_search(req: SearchRequest):
    kb = rag.get_knowledge_base()
    try:
        hits = await asyncio.to_thread(kb.search, req.query, max(1, min(req.top_k, 10)))
    except (rag.IndexNotBuilt, rag.EmbedderMismatch) as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {
        "embedder_id": kb.embedder.embedder_id,
        "collection": kb.collection_name,
        "results": [h.as_dict() for h in hits],
    }


@app.get("/memories")
async def memories(request: Request, user_id: str = MEM0_USER_ID, limit: int = 50):
    # Another site open in the same browser must not be able to read the founder's memories.
    if not origin_allowed(request.headers.get("origin")):
        raise HTTPException(status_code=403, detail="origin not allowed")
    store = memory_store()
    if store is None:
        return {"memories": [], "error": "memory disabled"}
    data = await store.get_all(user_id=user_id, limit=limit, filters={"user_id": user_id})
    return {"memories": data.get("results", [])}


@app.get("/health")
async def health():
    return {"status": "ok", "mode": config.MODE}


def citations_from(output: str) -> list[dict]:
    return [
        {"source": m.group("source").strip(), "url": m.group("url")}
        for m in SOURCE_HEADER.finditer(output)
    ]


class TextConversation:
    """One founder <-> agent conversation over the text transport."""

    def __init__(self, mode: str, idea: str | None) -> None:
        self.mode = "vc" if mode == "vc" else "mentor"
        self.idea = idea or None
        self.agent: Assistant | None = None
        self.session: AgentSession | None = None
        self.llm = make_text_llm()
        self._greeting: asyncio.Queue[str] = asyncio.Queue()

    async def start(self) -> dict:
        memory_context = await fetch_initial_memories()
        self.agent = Assistant(self.idea, memory_context, self.mode)
        self.session = AgentSession(llm=self.llm)
        attach_memory_handlers(self.session, self.agent, voice=False)

        @self.session.on("conversation_item_added")
        def _capture(event):
            if getattr(event.item, "role", None) == "assistant":
                self._greeting.put_nowait(event.item.text_content or "")

        await self.session.start(self.agent)
        handle = self.session.generate_reply(instructions=greeting_instructions(self.idea, self.mode))
        await handle
        text = await asyncio.wait_for(self._greeting.get(), timeout=30)
        return {"type": "agent_message", "text": text, "citations": [], "tools": [], "memories": []}

    async def send(self, text: str) -> dict:
        assert self.session and self.agent
        self.agent.chat_history.append({"role": "founder", "content": text})
        result = await self.session.run(user_input=text)

        reply, tools, citations, recalled = [], [], [], []
        for ev in result.events:
            if isinstance(ev, FunctionCallEvent):
                tools.append({"name": ev.item.name, "arguments": ev.item.arguments})
            elif isinstance(ev, FunctionCallOutputEvent):
                if ev.item.name == "search_knowledge_base":
                    citations.extend(citations_from(ev.item.output))
                elif ev.item.name == "recall_memory":
                    recalled.extend(parse_memory_output(ev.item.output))
            elif isinstance(ev, ChatMessageEvent) and ev.item.role == "assistant":
                reply.append(ev.item.text_content or "")

        # Stored after the turn so a question never recalls itself.
        if should_store_in_memory(text):
            await store_in_memory(text)
        return {
            "type": "agent_message",
            "text": "\n\n".join(r for r in reply if r),
            "citations": citations,
            "tools": tools,
            "memories": recalled,
        }

    async def report(self) -> dict:
        assert self.agent
        data = await self.agent.generate_post_call_report()
        return {"type": "vc_report", "data": data}

    async def close(self) -> None:
        if self.session:
            await self.session.aclose()
        await self.llm.aclose()


@app.websocket("/ws/chat")
async def chat(ws: WebSocket, mode: str = "mentor", idea: str | None = None):
    # Without this, any page the founder visits could open a conversation on their keys.
    if not origin_allowed(ws.headers.get("origin")):
        await ws.close(code=1008)
        return
    await ws.accept()
    conv = TextConversation(mode, idea)
    try:
        await ws.send_json(await conv.start())
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "user_message" and (msg.get("text") or "").strip():
                await ws.send_json(await conv.send(msg["text"].strip()))
            elif kind == "generate_report":
                await ws.send_json(await conv.report())
            else:
                await ws.send_json({"type": "error", "message": f"unsupported message {kind!r}"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("text conversation failed")
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        await conv.close()


if config.DIAGNOSTICS:
    @app.get("/_diag/egress")
    async def egress_diagnostics():
        return await probe_egress("agent-server")

    @app.get("/_diag/providers")
    async def provider_diagnostics():
        kb = rag.get_knowledge_base()
        return {
            "mode": config.MODE,
            "text_llm": type(make_text_llm()).__name__,
            "embedder_id": kb.embedder.embedder_id,
            "collection": kb.collection_name,
            "memory": type(memory_store()).__name__,
        }

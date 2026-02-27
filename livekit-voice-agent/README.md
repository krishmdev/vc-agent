# Launchpad voice agent

The Sequoia mentor and VC personas, their tools, the knowledge base, and long-term memory. Part
of [Launchpad](../README.md).

Two entry points share the same agent code (`mentor.py`, `personas.py`):

- `agent.py` is the LiveKit worker. It runs a real-time voice session on Gemini native audio
  (`gemini-2.5-flash-native-audio-preview-12-2025`; voice Puck for the mentor, Kore for the VC),
  with no separate STT/TTS. An earlier hackathon version used GPT-4o, AssemblyAI and Cartesia;
  none of that is used any more.
- `server.py` (port 8001) serves `POST /kb/search` for the research agent, `GET /memories`, and
  `WS /ws/chat`. The WebSocket is a text transport that runs the same `Assistant` and tools
  inside a livekit-agents `AgentSession`: a scripted LLM (`scripted_llm.py`) in offline mode,
  Gemini Flash as a text model in live mode.

## Tools and memory

- `search_knowledge_base` does semantic search over the Sequoia collection (`rag.py`). The query
  runs in a thread so it doesn't block the audio loop.
- `recall_memory` searches long-term memory. Sessions are also primed with recent memories, and
  meaningful founder turns are written back. The backend comes from `memory.make_memory_store()`:
  Mem0 cloud in live mode (`MEM0_API_KEY`), or `LocalMemoryStore` (SQLite, same
  `add` / `get_all` / `search` calls) offline or with `VC_AGENT_MEMORY=local`.
- The post-call VC report is written by `gemini-2.5-flash-lite` in live mode, or assembled from
  the founder's own sentences offline (`offline_report.py`). It's posted to the frontend's
  `/api/vc-report`.

## Knowledge base

`data/` holds 116 Sequoia podcast transcripts and `sequoia_data.json` (scraped sequoiacap.com
pages). `ingest.py` cleans them, dedupes repeated pages, and chunks them (2,000 characters with
400 overlap, 11,741 chunks).

```bash
uv sync
uv run python model_store.py fetch        # all-MiniLM-L6-v2 at the revision in ../models.lock
uv run python ingest.py --embedder local  # offline collection, no network
uv run python ingest.py --embedder openai # text-embedding-3-small, needs OPENAI_API_KEY
```

Each build is a new collection tagged with its `embedder_id`, made active by an atomic pointer
swap once every chunk is embedded. A failed build is deleted. Queries against a collection built
by another embedder are refused. Stop the servers before rebuilding.

## Run

```bash
uv run uvicorn server:app --port 8001   # KB search + text chat (needed in both modes)
uv run agent.py dev                      # LiveKit worker (live mode only; refuses offline)
uv run agent.py console                  # talk to it in the terminal
```

Env (`.env.local` here or at the repo root; ignored in offline mode): `LIVEKIT_URL`,
`LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `GEMINI_API_KEY`, `OPENAI_API_KEY` (OpenAI collection),
`MEM0_API_KEY`, plus `KB_EMBEDDER=openai|local`.

## Tests

`uv run pytest` (sockets disabled except localhost). Covers the local memory store, index
generations (including a provider failure halfway through a build, and a swap by another
process), and the text transport end to end: knowledge-base citation, memory stored in one
conversation and recalled in the next, and the VC report.

`scripts/voice_smoke.py` is the live headless check: it joins a LiveKit room as a founder,
plays a WAV question, and records the agent's audio and transcriptions. See
[docs/verification.md](../docs/verification.md).

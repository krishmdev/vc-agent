# Launchpad — Voice Agent (Sequoia Startup Mentor)

A real‑time voice AI that acts as a **Sequoia Capital partner**, drawing wisdom
from 100+ Sequoia podcast transcripts and articles. It runs two personas — a warm
**mentor** and a skeptical **VC** — grounded in a RAG knowledge base and backed by
long‑term memory. Part of the [Launchpad](../README.md) platform.

Built with **LiveKit Agents**, **Google Gemini Live** (native audio), **ChromaDB**,
and **Mem0**.

## Features

- **Real‑time voice** via **Gemini Live** (`gemini-2.5-flash-native-audio-preview-12-2025`)
  — native speech in/out, low latency, no separate STT/TTS stack.
- **Two personas** (selected via LiveKit room metadata):
  - **Mentor** (voice: *Puck*) — relaxed but sharp; always grounds advice in a real
    story from the knowledge base.
  - **VC** (voice: *Kore*) — runs a high‑stakes pitch simulation and delivers a
    pass/fail verdict.
- **RAG** (`search_knowledge_base` tool) — semantic search over a **ChromaDB**
  vector store built from Sequoia transcripts + scraped articles, embedded with
  **OpenAI `text-embedding-3-small`**.
- **Long‑term memory** (`recall_memory` tool) — **Mem0** stores meaningful things
  the founder says across sessions and primes each new call with prior context.
- **Post‑call VC report** — on request, summarizes the pitch into a structured
  report (`gemini-2.0-flash-lite-preview-02-05`) and POSTs it to the frontend at
  `http://localhost:3000/api/vc-report`.

## Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management
- A **LiveKit Cloud** project
- API keys: **Gemini** (voice + reports), **OpenAI** (RAG embeddings), **Mem0**
  (optional — memory)

## Setup

### 1. Install

```bash
uv sync
```

### 2. Configure environment

Create `.env.local` here (or use the shared `.env.local` at the repo root — both
are loaded):

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

GEMINI_API_KEY=your-gemini-key      # real-time audio + report generation
OPENAI_API_KEY=your-openai-key      # ChromaDB embeddings (RAG)
MEM0_API_KEY=your-mem0-key          # optional; long-term memory
```

> If `MEM0_API_KEY` is omitted, the agent still runs — memory features are simply
> disabled.

### 3. Build the knowledge base

The Sequoia source data ships in `data/` (100+ `.txt` transcripts + `sequoia_data.json`).
Run the ingestion script once to chunk, embed, and index it into ChromaDB
(`chroma_db/` is created locally and git‑ignored):

```bash
uv run ingest.py
```

### 4. Run the agent

```bash
uv run agent.py dev        # run as a LiveKit worker (used by the web app)
# or
uv run agent.py console    # talk to it directly in your terminal
```

## Project structure

- `agent.py` — agent logic, mentor/VC personas, memory + RAG tools, Gemini Live
  session, and post‑call report generation.
- `rag.py` — ChromaDB client + semantic `search()` over the `knowledge_base` collection.
- `ingest.py` — cleans, chunks (2000/400), and indexes `data/` into ChromaDB.
- `data/` — Sequoia podcast transcripts and `sequoia_data.json` (scraped articles).

## How it works

1. **Ingestion** — `ingest.py` cleans transcripts/articles, splits them into
   overlapping chunks, and indexes them in ChromaDB using OpenAI embeddings.
2. **Session start** — the web app mints a LiveKit token embedding
   `{ startupIdea, agentMode }`; the agent reads it to pick the persona and voice,
   and primes context from Mem0.
3. **Per turn** — the agent retrieves relevant Sequoia insights via RAG and recalls
   prior context via Mem0, then responds in Gemini Live's native voice. Meaningful
   user statements are written back to Mem0.
4. **VC report** — when the client sends a `generate_report` data message, the
   agent produces a structured report (diagnosis, strengths, gaps, "terrifying
   questions", next steps, extracted fields) and POSTs it to the dashboard.

> **History note:** an earlier version of this agent used OpenAI GPT‑4o with
> AssemblyAI (STT) and Cartesia (TTS). The current implementation uses **Gemini
> Live** for native real‑time audio; OpenAI is now used only for RAG embeddings.

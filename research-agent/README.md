# Launchpad — Research Agent

The AI research backend for [Launchpad](../README.md). A **FastAPI** service
(port **8000**) that orchestrates Google Gemini and third‑party data APIs to power
market research, customer discovery, resource guides, and pitch‑deck generation.

Built with **FastAPI**, **Uvicorn**, and **Google Gemini** (`google-genai`).

## Capabilities

- **Market research chat** (`/chat`) — the first turn runs a **Deep Research**
  agent (`deep-research-pro-preview-12-2025`) that produces a structured, sourced
  "Problem Space Assessment." Follow‑up turns use **`gemini-2.5-flash` with Google
  Search grounding** for fast, cited answers.
- **Customer reach‑out** (`/customer-reachout`):
  - **B2C** → Gemini extracts keywords, **PRAW** finds relevant subreddits, and
    Gemini writes a tailored outreach strategy per community + offline venue ideas.
  - **B2B** → Gemini parses the ICP into **Apollo.io** search params, queries
    Apollo for people + organizations, and falls back to Gemini‑generated sample
    leads if Apollo returns nothing.
- **Resource guides** (`/generate_resource_article`, `/resource_chat`) — generate
  and chat about tactical, Sequoia‑partner‑style startup guides
  (`gemini-2.5-flash` + Google Search).
- **Pitch deck** (`/generate-slides`) — assembles a 12‑slide Sequoia‑style deck
  from the dashboard answers, filling gaps with Gemini, via the **Manus** API
  (`nano_banana_pro`, `.pptx`) with a structured‑JSON Gemini fallback
  (`gemini-2.0-flash`). See `slide_generator.py`.

Long‑running work runs as **background tasks** with a `task_id` + polling pattern.
Sessions and tasks are held in in‑memory dicts (see [caveats](#notes--caveats)).

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Start a research turn (deep research on turn 1, fast chat after). Returns `task_id`. |
| `GET` | `/chat/status/{task_id}` | Poll a chat / reach‑out / slide task (`processing` / `completed` / `failed`). |
| `POST` | `/customer-reachout` | Find B2C communities or B2B leads for an ICP. Returns `task_id`. |
| `POST` | `/generate_resource_article` | Generate a tactical startup guide (synchronous). |
| `POST` | `/resource_chat` | Chat about a generated guide (synchronous). |
| `POST` | `/generate-slides` | Generate a 12‑slide pitch deck from dashboard modules. Returns `task_id`. |
| `GET` | `/health` | Health check. |

CORS is open to `http://localhost:3000` / `http://127.0.0.1:3000` for the frontend.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Environment variables

The service loads `.env` from this directory, the CWD, and the repo root. Create a
`.env` (or use the shared root `.env`):

```env
GEMINI_API_KEY=your-gemini-key          # required — all research/generation

# B2C customer discovery (optional)
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_USER_AGENT=BrownHacksResearchAgent/1.0   # optional; this is the default

# B2B customer discovery (optional)
APOLLO_API_KEY=your-apollo-key

# Pitch-deck generation (optional; falls back to Gemini)
MANUS_API_KEY=your-manus-key
MANUS_API_URL=https://api.manus.im/v1           # optional; this is the default
```

Every integration **degrades gracefully**: missing Reddit/Apollo/Manus keys fall
back to Gemini‑generated samples or helpful placeholder messages.

## Run

```bash
uvicorn main:app --reload --port 8000
```

## Tests

```bash
pytest        # test_endpoints.py — mocked Gemini, no real API calls
```

## Notes & caveats

- **In‑memory state.** Chat sessions (`chat_sessions`) and tasks (`active_tasks`)
  live in Python dicts and reset on restart. Use Redis/Postgres for production.
- **Preview model IDs.** `deep-research-pro-preview-12-2025` and several `gemini-*`
  IDs are pinned in the code; adjust them if they aren't available on your API tier.

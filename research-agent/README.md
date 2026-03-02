# Launchpad research agent

FastAPI service (port 8000) for market research, resource guides grounded in the knowledge base,
customer discovery, and pitch decks. Part of [Launchpad](../README.md).

- `/chat`: the first turn runs Gemini's Deep Research agent (`deep-research-pro-preview-12-2025`)
  with the team's "Problem Space Specialist" prompt (`prompts.py`); later turns use
  `gemini-2.5-flash` with Google Search. Jobs are asyncio tasks; poll `/chat/status/{task_id}`
  for `queued`, `running` (with progress notes), `completed`, `failed` or `cancelled` (shutdown,
  the two-hour backstop; a live run is cancelled on Gemini's side too).
- `/generate_resource_article`, `/resource_chat`: retrieve passages from the Sequoia knowledge
  base (via `KB_SERVICE_URL`, the voice agent's `server.py`) and write a guide that cites them as
  `[n]`. The response includes `citations`.
- `/customer-reachout`: B2C (Gemini keywords, PRAW subreddit search, per-community strategies) or
  B2B (Gemini → Apollo people and company search, with Gemini samples as the fallback).
- `/generate-slides`: a 12-slide deck through Manus, or Gemini JSON when there's no Manus key.

Everything is async: `google-genai`'s `client.aio`, `httpx` for Apollo and Manus, and PRAW
through `run_in_threadpool`.

## Offline mode

With `VC_AGENT_MODE=offline`, `FixtureResearchProvider` replays one of the three recorded runs
in `fixtures/research/` through the same task flow. Each fixture stores the agent id, date,
prompt sha256, usage, the thought/search notes and the report. The replay's banner says whether
the app's prompt hashes to the recorded one, is the same idea with different context, or falls
back to the nearest sample idea. Guides become extractive (quoted, cited sentences), and
reach-out and slides are turned off with a message.

Re-recording is a separate, paid, network step:
`uv run python scripts/record_research_fixtures.py [--only SLUG] [--force]`.

## Run and test

```bash
uv sync
uv run uvicorn main:app --port 8000   # no --reload: tasks and sessions live in memory
uv run pytest                          # offline, sockets disabled except localhost
```

Keys (`research-agent/.env` or the repo root `.env` / `.env.local`; ignored offline):
`GEMINI_API_KEY`, and optionally `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `APOLLO_API_KEY`,
`MANUS_API_KEY`.

Tasks and sessions are in-memory only. After a restart, a status poll returns 404 and a
follow-up question starts a new, paid deep-research run.

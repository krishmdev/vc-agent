# Verification

What was checked, how, and what wasn't. All runs were on 2026-03-01 on an M1 Pro MacBook
(macOS 26), with the result files in [`verification/`](verification/) and a host manifest in
[`verification/manifest-2026-03-01.json`](verification/manifest-2026-03-01.json).

## Offline mode (no keys, no network)

| Check | How | Result |
|---|---|---|
| Python tests | `make test`: pytest with `pytest-socket` (`--disable-socket`, localhost only), `VC_AGENT_MODE=offline`, keys removed | voice agent 16 passed, research agent 11 passed |
| Frontend | `npx eslint .`, `npx tsc --noEmit`, `next build` (live and offline bundles) | 0 lint errors (existing code has warnings), both builds pass |
| Offline e2e, macOS | `offline-run make e2e-offline`: the whole process tree (Next.js, FastAPI research agent, voice-agent server, Playwright and Chromium) under a `sandbox-exec` profile that denies outbound network except localhost, with provider keys unset and HF offline | 5 passed |
| Offline e2e, Linux | fresh `git clone`, then `docker run … make deps models build-offline` (network allowed), then `docker run --network none … make e2e-offline`, i.e. what the CI job does | 5 passed |
| Egress canaries | `e2e/egress.spec.ts` asks each backend process type (Next.js server runtime, research agent, voice-agent server) to open TCP connections to 1.1.1.1, api.openai.com, generativelanguage.googleapis.com and huggingface.co from inside that process | under the sandbox every connect failed with EPERM; in the `--network none` container with ENETUNREACH / DNS failure |
| Canary companion | `make egress-companion` (same spec, unsandboxed, `EXPECT_EGRESS=open`) | all 12 probes connected, so the offline result isn't vacuous |
| Fixture prompts | test recomputes the app's first-turn prompt for each sample idea and compares its sha256 with the recording | all 3 match |

The e2e journey: submit a sample idea, chat with the mentor (the answer carries a Sequoia KB
citation and the founder's pricing statement lands in the local memory store, which starts
empty), open the research panel (queued, then running with the recorded progress notes, then
the rendered report with its exact-recording banner and `[cite: n]` links), generate a resource
guide in the drawer (numbered Sequoia sources), then ask the floating mentor what was said about
pricing (it recalls "$300 a month" and cites the KB). The browser also aborts and records any
non-localhost request; none were made.

What the offline path shares with voice: the `Assistant` class, persona prompts, both tools,
memory capture, and the report builder all run inside a real livekit-agents `AgentSession`
(text mode) with a scripted LLM. What it does not exercise: the realtime native-audio turn
loop (audio in, VAD/turn detection, audio out). That part is only covered by the live run below.

## Live runs (Krish's keys)

| What | Model / service | Result | File |
|---|---|---|---|
| Deep research, recorded as fixtures | `deep-research-pro-preview-12-2025` | 3 runs, 234–244 s each, 159k–198k input tokens, 8.6k–11.9k output, 14.9k–20.2k thought tokens, 13–15 searches | `research-agent/fixtures/research/*.json` |
| Follow-up answers for the fixtures | `gemini-2.5-flash` + Google Search | 3 answers recorded | same files |
| Deep research through the running server | `research-agent/scripts/live_smoke_research.py`: `POST /chat`, then polling `/chat/status` | queued → running → completed in 202 s, 19.7k-char report. 41 `/health` probes during the run: median 19.8 ms, max 314 ms, so the handlers weren't blocking | `verification/live-research-2026-03-01.json` |
| KB-grounded guides | `research-agent/scripts/live_guides.py`, `gemini-2.5-flash` with 4 retrieved passages | 2 guides; they cited excerpts [2],[4] and [1]–[4]. With the Google Search tool attached, Gemini dropped every citation marker, so Search is now only used when the KB returns nothing | `verification/live-guides-2026-03-01.jsonl` |
| Mem0 cloud | `livekit-voice-agent/scripts/mem0_smoke.py`, `AsyncMemoryClient` through `memory.make_memory_store()` | add queued, fact extracted ("User plans to charge each veterinary clinic $300 per month…"), found by `search("pricing")`; test user deleted afterwards. Also found that `get_all` without `filters` returns HTTP 400, so session priming had been failing; fixed | `verification/mem0-2026-03-01.json` |
| LiveKit voice session, headless | LiveKit Cloud + `gemini-2.5-flash-native-audio-preview-12-2025` | `scripts/voice_smoke.py` joined a fresh room as a founder, played a synthesized question, and listened. Agent joined, heard the question (transcript: "How did the find its first customers…"), called `search_knowledge_base` ("Airbnb first customers acquisition strategy"), wrote to Mem0, and answered aloud: 27.6 s of agent audio, answer grounded in the Airbnb/Brian Chesky transcript. The tool calls and Mem0 writes are in the worker log, not the JSON | `verification/livekit-voice-2026-03-01.json`, `verification/livekit-voice-2026-03-01.worker.log` |

The voice run used `KB_EMBEDDER=local` (the MiniLM collection) and a throwaway Mem0 user id,
deleted afterwards. That run's JSON was reduced to final transcript segments by a one-off filter
at the time (the `note` field in the file says so); `voice_smoke.py` now keeps only final
segments itself. The worker log file holds only the tool, memory and transcript lines for the
smoke window. The research, guide and Mem0 driver scripts were committed after those runs,
written from the commands used. The research file's early `guide` block, from before the
citation fix, was removed; `live-guides-2026-03-01.jsonl` has the guide results.

Rough spend (an estimate, not a bill): four deep-research runs at roughly $1 each at Pro-tier
token prices, plus a few cents of Flash, native audio and Mem0.

## Not verified

- **OpenAI-embedding RAG.** `make index-live` failed with `insufficient_quota`: the OpenAI key
  in the project env files has no credits. The failed build was cleaned up as designed (partial
  collection deleted, active pointer unchanged), but no OpenAI-embedding query has been run. The
  live runs above used the MiniLM collection instead.
- **Browser voice.** The headless run covers the agent side of LiveKit and Gemini native audio;
  the web app's `LiveKitRoom` microphone path in a real browser wasn't driven.
- **Gemini deep-research quality.** The reports are what the agent returned; nobody fact-checked
  them. Follow-up answers in offline mode are extractive, not model-written.
- **Live research progress.** Polling the interactions API only returns thought and search steps
  once a run completes, so live mode shows elapsed time until the report arrives, and the
  recorded notes all carry the completion timestamp. The offline replay spreads them evenly.
- **GitHub Actions.** The workflow's steps were run locally (same container, same commands), but
  the workflow itself hasn't run on GitHub yet.
- Customer reach-out (Reddit, Apollo) and pitch-deck generation (Manus) weren't exercised; no
  keys for those services.

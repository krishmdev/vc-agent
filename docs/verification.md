# Verification

This log lists what was checked and what remains unverified. Live runs took place on 2026-03-01
(the founder-score tag recording on 2026-03-02) on an M1 Pro MacBook (macOS 26); the offline
counts below are from the 2026-03-02 runs at commit d707b0d (later commits touch only docs and
`scripts/sample_scores.py`). Result files are in [`verification/`](verification/), with a
host manifest in [`verification/manifest-2026-03-01.json`](verification/manifest-2026-03-01.json).

## Offline mode (no keys, no network)

| Check | How | Result |
|---|---|---|
| Python tests | `make test`: pytest with `pytest-socket` (`--disable-socket`, localhost only), `VC_AGENT_MODE=offline`, keys removed | voice agent 22 passed, research agent 135 passed |
| Frontend | `npx eslint .`, `npx tsc --noEmit`, `next build` (live and offline bundles) | 0 lint errors (existing code has warnings), both builds pass |
| Offline e2e, macOS | `offline-run make e2e-offline`: the whole process tree (Next.js, FastAPI research agent, voice-agent server, Playwright and Chromium) under a `sandbox-exec` profile that denies outbound network except localhost, with provider keys unset and HF offline | 6 passed (egress x4, journey, founder score) |
| Offline e2e, Linux | fresh `git clone` of d707b0d, then `docker run … make deps models build-offline index-offline` (network allowed), then `docker run --network none … make test lint e2e-offline`, i.e. what the CI job does | index 9,025 chunks, tests 22 + 135, lint clean, e2e 6 passed |
| Egress canaries | `e2e/egress.spec.ts` asks each backend process type (Next.js server runtime, research agent, voice-agent server) to open TCP connections to 1.1.1.1, api.openai.com, generativelanguage.googleapis.com and huggingface.co from inside that process | under the sandbox every connect failed with EPERM; in the `--network none` container with ENETUNREACH / DNS failure |
| Canary companion | `make egress-companion` (same spec, unsandboxed, `EXPECT_EGRESS=open`) | all 12 probes connected, so the offline result isn't vacuous |
| Offline index | `make index-offline` after pruning the crawl (see DATA_NOTICE): 116 transcripts and 499 sequoiacap.com pages | 9,025 chunks embedded with pinned MiniLM in 3 min 1 s on all cores; the new generation became active through the pointer swap |
| Founder samples | `scripts/sample_scores.py` rerun against the current code | output identical to `verification/founder-samples-offline.json` |
| Fixture prompts | test recomputes the app's first-turn prompt for each sample idea and compares its sha256 with the recording | all 3 match |

The e2e journey submits a sample idea, then chats with the mentor. The answer cites the Sequoia
knowledge base, and the founder's pricing statement is saved in the initially empty local memory
store. The research panel moves from queued to running with recorded progress notes, then shows
the report with its exact-recording banner and `[cite: n]` links. The resource drawer produces a
guide with numbered Sequoia sources. Finally, the floating mentor recalls "$300 a month" and cites
the knowledge base. The browser aborts and records non-localhost requests; it made none.

The offline path runs the same `Assistant` class, persona prompts, tools, memory capture, and
report builder inside a livekit-agents `AgentSession` in text mode, with a scripted LLM. It does
not exercise the real-time native-audio loop (audio input, VAD and turn detection, or audio
output). Only the live run below covers that path.

## Live runs (Krish's keys)

| What | Model / service | Result | File |
|---|---|---|---|
| Deep research, recorded as fixtures | `deep-research-pro-preview-12-2025` | 3 runs, 234-244 s each, 159k-198k input tokens, 8.6k-11.9k output, 14.9k-20.2k thought tokens, 13-15 searches | `research-agent/fixtures/research/*.json` |
| Follow-up answers for the fixtures | `gemini-2.5-flash` + Google Search | 3 answers recorded | same files |
| Deep research through the running server | `research-agent/scripts/live_smoke_research.py`: `POST /chat`, then polling `/chat/status` | queued → running → completed in 202 s, 19.7k-char report. 41 `/health` probes during the run: median 19.8 ms, max 314 ms, so the handlers weren't blocking | `verification/live-research-2026-03-01.json` |
| KB-grounded guides | `research-agent/scripts/live_guides.py`, `gemini-2.5-flash` with 4 retrieved passages | 2 guides; they cited excerpts [2],[4] and [1]-[4]. With the Google Search tool attached, Gemini dropped every citation marker, so Search is now only used when the KB returns nothing | `verification/live-guides-2026-03-01.jsonl` |
| Mem0 cloud | `livekit-voice-agent/scripts/mem0_smoke.py`, `AsyncMemoryClient` through `memory.make_memory_store()` | add queued, fact extracted ("User plans to charge each veterinary clinic $300 per month…"), found by `search("pricing")`; test user deleted afterwards. Also found that `get_all` without `filters` returns HTTP 400, so session priming had been failing; fixed | `verification/mem0-2026-03-01.json` |
| Founder-score domain tags, recorded | `research-agent/scripts/record_classifications.py`, `gemini-3-flash-preview` at temperature 0.1, thinking off (sierra-demo's classification settings) | 8 classifications (founder and company for the four fictional sample founders), recorded 2026-03-02 after 503 retries; the file header pins model, temperature, prompt and taxonomy hashes | `research-agent/scoring/recordings/classifications.json` |
| LiveKit voice session, headless | LiveKit Cloud + `gemini-2.5-flash-native-audio-preview-12-2025` | `scripts/voice_smoke.py` joined a fresh room as a founder, played a synthesized question, and listened. Agent joined, heard the question (transcript: "How did the find its first customers…"), called `search_knowledge_base` ("Airbnb first customers acquisition strategy"), wrote to Mem0, and answered aloud: 27.6 s of agent audio, answer grounded in the Airbnb/Brian Chesky transcript. The tool calls and Mem0 writes are in the worker log, not the JSON | `verification/livekit-voice-2026-03-01.json`, `verification/livekit-voice-2026-03-01.worker.txt` |

The voice run used `KB_EMBEDDER=local` (the MiniLM collection, then the 11,741-chunk index built
before the crawl was pruned of off-site pages) and a throwaway Mem0 user id,
which was deleted afterwards. A one-off filter reduced that run's JSON to final transcript
segments at the time, as noted in the file. `voice_smoke.py` now keeps only final segments itself.
The worker log contains only tool, memory, and transcript lines from the smoke window. The
research, guide, and Mem0 driver scripts were committed after those runs, based on the commands
used. The research file's early `guide` block, created before the citation fix, was removed;
`live-guides-2026-03-01.jsonl` has the guide results.

Estimated spend, not a bill: four deep-research runs at roughly $1 each at Pro-tier token prices,
plus a few cents for Flash, native audio, and Mem0.

Founder-score sample scorecards, offline with the recorded tags: `research-agent/scripts/sample_scores.py`
writes `verification/founder-samples-offline.json`; the same values are pinned in
`research-agent/tests/test_founder_api.py`. The keyword-lexicon path (no recordings) gives
different domain-fit scores and is pinned separately in `tests/test_scoring.py`.

An earlier attempt on 2026-03-01 used `gemini-2.5-flash` with thinking on; with a 512-token cap
the JSON came back truncated. sierra-demo itself turns thinking off for flash models, which the
port now does too.

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
- **Cancelling a live deep-research run.** On timeout or job cancellation the provider calls
  `interactions.cancel`. That is tested against a fake client only; no live run was cancelled.
- **GitHub Actions.** The workflow's steps were run locally (same container, same commands), but
  the workflow itself hasn't run on GitHub yet.
- Customer reach-out (Reddit, Apollo) and pitch-deck generation (Manus) weren't exercised; no
  keys for those services.

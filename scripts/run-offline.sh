#!/usr/bin/env bash
# Offline demo: the three services on localhost with every provider swapped for a local one.
# Needs `make setup` and `make index-offline` first. For a network-proof run, wrap it in a
# sandbox (see README). Ctrl+C stops everything.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"

export VC_AGENT_MODE=offline HF_HUB_OFFLINE=1 NEXT_TELEMETRY_DISABLED=1
unset OPENAI_API_KEY GEMINI_API_KEY GOOGLE_API_KEY MEM0_API_KEY LIVEKIT_API_KEY LIVEKIT_API_SECRET || true

pids=()
cleanup() { kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Single process, no --reload: research tasks live in memory.
(cd "$root/livekit-voice-agent" && exec .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8001) &
pids+=($!)
(cd "$root/research-agent" && exec .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000) &
pids+=($!)
(cd "$root/frontend" && NEXT_DIST_DIR=.next-offline NEXT_PUBLIC_VC_AGENT_MODE=offline exec npx next start -H 127.0.0.1 -p 3000) &
pids+=($!)

echo "Offline demo: http://127.0.0.1:3000  (research agent :8000, mentor/KB server :8001)"
wait

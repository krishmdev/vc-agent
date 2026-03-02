"""Runtime configuration shared by the research agent modules.

VC_AGENT_MODE=offline swaps every paid provider for a local one: recorded deep-research
fixtures, extractive guides over the offline knowledge-base collection, and no calls to
Gemini, Reddit, Apollo or Manus. Nothing in offline mode reads provider keys.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent

MODE = os.environ.get("VC_AGENT_MODE", "live").strip().lower()
if MODE not in {"live", "offline"}:
    raise RuntimeError(f"VC_AGENT_MODE must be 'live' or 'offline', got {MODE!r}")
OFFLINE = MODE == "offline"

if not OFFLINE:
    # research-agent/.env, then the working directory, then the repo root.
    load_dotenv(HERE / ".env")
    load_dotenv()
    load_dotenv(HERE.parent / ".env")
    load_dotenv(HERE.parent / ".env.local")

DIAGNOSTICS = os.environ.get("VC_AGENT_DIAGNOSTICS") == "1"

# The voice-agent package owns the knowledge base (Chroma + embedder); its server.py serves it.
KB_SERVICE_URL = os.environ.get("KB_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")

FRONTEND_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]

# Host headers the service answers to. It listens on 127.0.0.1; this stops DNS-rebinding pages
# from reaching it under another name. Add a hostname here when deploying behind a proxy.
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

DEEP_RESEARCH_AGENT = os.environ.get("DEEP_RESEARCH_AGENT", "deep-research-pro-preview-12-2025")
CHAT_MODEL = os.environ.get("RESEARCH_CHAT_MODEL", "gemini-2.5-flash")
# gemini-2.0-flash, which the reach-out and slide code originally used, has been retired.
UTILITY_MODEL = os.environ.get("RESEARCH_UTILITY_MODEL", "gemini-2.5-flash")

FIXTURE_DIR = Path(os.environ.get("RESEARCH_FIXTURE_DIR", HERE / "fixtures" / "research"))
# Total wall-clock seconds a fixture replay takes from queued to completed.
FIXTURE_REPLAY_SECONDS = float(os.environ.get("RESEARCH_FIXTURE_REPLAY_SECONDS", "8"))


# Offline founder scores for submitted profiles are computed as of this date, so they're
# reproducible; sample founders use the date stored in their fixture. Live requests must send
# as_of (the browser sends the founder's local date).
SCORING_AS_OF = os.environ.get("SCORING_AS_OF", "2026-03-01")


def gemini_api_key() -> str | None:
    if OFFLINE:
        return None
    return os.environ.get("GEMINI_API_KEY")

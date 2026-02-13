"""Mode and paths for the voice agent, its text transport server, and the knowledge base.

VC_AGENT_MODE=offline selects local providers only: the MiniLM knowledge-base collection, the
SQLite memory store, and the scripted LLM for text conversations. Env files are not loaded in
offline mode, so a stray .env.local can't put provider keys back into the process.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

MODE = os.environ.get("VC_AGENT_MODE", "live").strip().lower()
if MODE not in {"live", "offline"}:
    raise RuntimeError(f"VC_AGENT_MODE must be 'live' or 'offline', got {MODE!r}")
OFFLINE = MODE == "offline"

if not OFFLINE:
    load_dotenv(HERE / ".env.local")
    load_dotenv(REPO_ROOT / ".env.local")

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")  # Chroma telemetry

DIAGNOSTICS = os.environ.get("VC_AGENT_DIAGNOSTICS") == "1"

DATA_DIR = HERE / "data"
CHROMA_DIR = Path(os.environ.get("CHROMA_DB_DIR", HERE / "chroma_db"))
MODELS_DIR = Path(os.environ.get("VC_AGENT_MODELS_DIR", REPO_ROOT / ".models"))
MODELS_LOCK = REPO_ROOT / "models.lock"

# "local" (MiniLM ONNX) or "openai" (text-embedding-3-small). Offline mode is always local.
KB_EMBEDDER = "local" if OFFLINE else os.environ.get("KB_EMBEDDER", "openai").strip().lower()

# "mem0" (cloud, live default) or "local" (SQLite). Offline mode is always local.
MEMORY_BACKEND = "local" if OFFLINE else os.environ.get("VC_AGENT_MEMORY", "mem0").strip().lower()
MEMORY_DB = Path(os.environ.get("VC_AGENT_MEMORY_DB", HERE / ".data" / "memory.sqlite3"))
# Mem0 user id shared with the frontend's /api/memories route.
MEMORY_USER_ID = os.environ.get("MEM0_USER_ID", "sequoia-mentor-agent")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
REPORT_MODEL = os.environ.get("VC_REPORT_MODEL", "gemini-2.5-flash-lite")
VOICE_MODEL = os.environ.get("VOICE_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")
TEXT_MODEL = os.environ.get("TEXT_CHAT_MODEL", "gemini-2.5-flash")


def key(name: str) -> str | None:
    """Provider keys are invisible in offline mode even if the environment has them."""
    if OFFLINE:
        return None
    return os.environ.get(name) or None

import os
import sys
from pathlib import Path

os.environ["VC_AGENT_MODE"] = "offline"
os.environ["RESEARCH_FIXTURE_REPLAY_SECONDS"] = "0.6"
for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "REDDIT_CLIENT_ID", "APOLLO_API_KEY", "MANUS_API_KEY"):
    os.environ.pop(key, None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

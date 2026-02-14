import os
import sys
from pathlib import Path

# Tests always run the offline composition; provider keys are dropped before config is imported.
os.environ["VC_AGENT_MODE"] = "offline"
for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "MEM0_API_KEY", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
    os.environ.pop(key, None)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

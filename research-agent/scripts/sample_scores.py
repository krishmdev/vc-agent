"""Offline scorecards for the four synthetic sample founders, as the app serves them.

Runs the research agent in offline mode in-process (no network) and writes the composites and
signal scores the README's founder-score section refers to.

    VC_AGENT_MODE=offline uv run python scripts/sample_scores.py > ../docs/verification/founder-samples-offline.json
"""

import contextlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("VC_AGENT_MODE", "offline")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

# 127.0.0.1 because the app only answers ALLOWED_HOSTS; the startup banner goes to stderr so
# stdout stays JSON.
with contextlib.redirect_stdout(sys.stderr), TestClient(main.app, base_url="http://127.0.0.1") as client:
    rows = []
    for sample in client.get("/founder/samples").json():
        card = client.get(f"/founder/samples/{sample['id']}/score").json()
        rows.append({
            "id": sample["id"],
            "name": sample["name"],
            "synthetic": sample["synthetic"],
            "as_of": card["as_of"],
            "classifier": card["classifier"],
            "composite": card["composite"]["score"],
            "band": card["composite"]["band"],
            "signals": {s["key"]: s["score"] for s in card["signals"]},
        })
print(json.dumps({"engine": "sierra-demo founder scoring, ported", "mode": "offline", "samples": rows}, indent=2))
